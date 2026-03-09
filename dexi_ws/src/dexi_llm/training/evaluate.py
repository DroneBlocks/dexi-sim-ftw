#!/usr/bin/env python3
"""Evaluate fine-tuned GGUF models against the validation set.

Compares tool-call accuracy between models by checking:
  1. tool_call presence (should the model call a tool or refuse?)
  2. tool name (correct tool?)
  3. service/topic (correct ROS 2 endpoint?)
  4. key arguments (correct command, color, pin, etc.?)

Requirements:
    pip install llama-cpp-python

Usage:
    # Evaluate single model
    python training/evaluate.py --model models/dexi-qwen2.5-1.5b-q4_k_m.gguf

    # Compare two models side by side
    python training/evaluate.py \
        --model models/dexi-qwen2.5-1.5b-q4_k_m.gguf \
        --model models/dexi-llama-3.2-1b-q4_k_m.gguf

    # Use a subset of examples
    python training/evaluate.py --model models/dexi-qwen2.5-1.5b-q4_k_m.gguf --limit 20

    # Use training data instead of validation
    python training/evaluate.py --model models/dexi-qwen2.5-1.5b-q4_k_m.gguf --dataset training/dataset/train.jsonl
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

TRAINING_DIR = Path(__file__).parent
CONFIG_DIR = TRAINING_DIR.parent / "dexi_llm" / "config"
DATASET_DIR = TRAINING_DIR / "dataset"


def load_system_block():
    with open(CONFIG_DIR / "tools.json") as f:
        tools = json.load(f)
    with open(CONFIG_DIR / "system_prompt.txt") as f:
        system_prompt = f.read().strip()

    tools_json = "\n".join(json.dumps(t, separators=(",", ":")) for t in tools)
    return (
        f"{system_prompt}\n\n"
        "# Tools\n\n"
        "You may call one or more functions to assist with the user query.\n\n"
        "You are provided with function signatures within <tools></tools> XML tags:\n"
        f"<tools>\n{tools_json}\n</tools>\n\n"
        "For each function call, return a json object with function name and "
        "arguments within <tool_call></tool_call> XML tags:\n"
        "<tool_call>\n"
        '{"name": <function-name>, "arguments": <args-json-object>}\n'
        "</tool_call>"
    )


def load_model_config(model_path):
    """Guess model config from filename."""
    with open(CONFIG_DIR / "models.json") as f:
        all_models = json.load(f)

    name = Path(model_path).stem.lower()
    for key, cfg in all_models.items():
        if key.replace(".", "").replace("-", "") in name.replace(".", "").replace("-", ""):
            return key, cfg

    # Default to qwen
    print(f"  WARNING: Could not detect model type from '{name}', defaulting to qwen2.5-1.5b")
    return "qwen2.5-1.5b", all_models["qwen2.5-1.5b"]


def parse_tool_call(text):
    """Extract the first tool_call from model output."""
    match = re.search(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def parse_expected(assistant_text):
    """Extract expected tool_call from the dataset's assistant response."""
    return parse_tool_call(assistant_text)


def compare_tool_calls(expected_tc, actual_tc):
    """Compare expected vs actual tool call. Returns (score dict, details)."""
    result = {
        "has_tool_call": False,
        "correct_tool": False,
        "correct_endpoint": False,
        "correct_args": False,
    }

    if expected_tc is None and actual_tc is None:
        # Both are refusals — correct
        return {k: True for k in result}, "correct refusal"

    if expected_tc is None and actual_tc is not None:
        result["has_tool_call"] = True  # it made a call, but shouldn't have
        return result, f"should refuse, got {actual_tc.get('name', '?')}"

    if expected_tc is not None and actual_tc is None:
        return result, "should call tool, got refusal"

    # Both have tool calls
    result["has_tool_call"] = True

    # Check tool name
    if actual_tc.get("name") == expected_tc.get("name"):
        result["correct_tool"] = True
    else:
        return result, f"tool: expected {expected_tc.get('name')}, got {actual_tc.get('name')}"

    # Check endpoint (service or topic)
    exp_args = expected_tc.get("arguments", {})
    act_args = actual_tc.get("arguments", {})
    endpoint_key = "service" if "service" in exp_args else "topic"

    if endpoint_key in exp_args:
        if act_args.get(endpoint_key) == exp_args.get(endpoint_key):
            result["correct_endpoint"] = True
        else:
            return result, f"{endpoint_key}: expected {exp_args.get(endpoint_key)}, got {act_args.get(endpoint_key)}"
    else:
        result["correct_endpoint"] = True  # no endpoint to check (e.g., get_topics)

    # Check key arguments (inside args, or top-level like msg_type)
    if "args" in exp_args and "args" in act_args:
        exp_inner = exp_args["args"]
        act_inner = act_args.get("args", {})
        mismatches = []
        for k, v in exp_inner.items():
            if k not in act_inner:
                mismatches.append(f"{k}: missing")
            elif act_inner[k] != v:
                mismatches.append(f"{k}: expected {v}, got {act_inner[k]}")
        if not mismatches:
            result["correct_args"] = True
        else:
            return result, "; ".join(mismatches)
    else:
        # Check msg_type for subscribe_once
        if "msg_type" in exp_args:
            if act_args.get("msg_type") == exp_args["msg_type"]:
                result["correct_args"] = True
            else:
                return result, f"msg_type: expected {exp_args['msg_type']}, got {act_args.get('msg_type')}"
        else:
            result["correct_args"] = True

    return result, "perfect"


def evaluate_model(model_path, examples, system_block):
    """Run all examples through a GGUF model and return results."""
    from llama_cpp import Llama

    model_name, model_cfg = load_model_config(model_path)
    tpl = model_cfg["chat_template"]
    stop_tokens = model_cfg["stop_tokens"]

    print(f"\nLoading {model_path}...")
    llm = Llama(
        model_path=str(model_path),
        n_ctx=2048,
        n_threads=4,
        verbose=False,
    )
    print(f"  Model loaded: {model_name}")

    results = []
    total_ms = 0

    for i, ex in enumerate(examples):
        user_msg = ex["messages"][0]["content"]
        assistant_msg = ex["messages"][-1]["content"]
        expected_tc = parse_expected(assistant_msg)

        # Build prompt
        prompt = tpl["bos"]
        prompt += tpl["system_prefix"] + system_block + tpl["system_suffix"]
        prompt += tpl["user_prefix"] + user_msg + tpl["user_suffix"]
        prompt += tpl["assistant_prefix"]

        # Generate
        t0 = time.time()
        output = llm(
            prompt,
            max_tokens=256,
            temperature=0.1,
            stop=stop_tokens,
        )
        elapsed_ms = (time.time() - t0) * 1000
        total_ms += elapsed_ms

        response = output["choices"][0]["text"]
        actual_tc = parse_tool_call(response)

        scores, detail = compare_tool_calls(expected_tc, actual_tc)
        results.append({
            "prompt": user_msg,
            "scores": scores,
            "detail": detail,
            "elapsed_ms": elapsed_ms,
            "response": response[:300],
        })

        status = "PASS" if all(scores.values()) else "FAIL"
        print(f"  [{i+1:3d}/{len(examples)}] [{status}] {user_msg[:50]:<50s} ({elapsed_ms:.0f}ms) {detail}")

    llm.close()
    return results, total_ms


def print_summary(model_path, results, total_ms):
    n = len(results)
    if n == 0:
        return

    counts = {k: 0 for k in ["has_tool_call", "correct_tool", "correct_endpoint", "correct_args"]}
    perfect = 0
    for r in results:
        for k, v in r["scores"].items():
            if v:
                counts[k] += 1
        if all(r["scores"].values()):
            perfect += 1

    print(f"\n{'='*70}")
    print(f"  {Path(model_path).stem}")
    print(f"{'='*70}")
    print(f"  Perfect match:    {perfect:3d}/{n} ({100*perfect/n:.1f}%)")
    print(f"  Has tool call:    {counts['has_tool_call']:3d}/{n} ({100*counts['has_tool_call']/n:.1f}%)")
    print(f"  Correct tool:     {counts['correct_tool']:3d}/{n} ({100*counts['correct_tool']/n:.1f}%)")
    print(f"  Correct endpoint: {counts['correct_endpoint']:3d}/{n} ({100*counts['correct_endpoint']/n:.1f}%)")
    print(f"  Correct args:     {counts['correct_args']:3d}/{n} ({100*counts['correct_args']/n:.1f}%)")
    print(f"  Avg latency:      {total_ms/n:.0f}ms")
    print(f"  Total time:       {total_ms/1000:.1f}s")

    # Show failures
    failures = [r for r in results if not all(r["scores"].values())]
    if failures:
        print(f"\n  Failures ({len(failures)}):")
        for r in failures:
            print(f"    \"{r['prompt'][:60]}\" -> {r['detail']}")

    return {
        "model": Path(model_path).stem,
        "n": n,
        "perfect": perfect,
        "perfect_pct": round(100 * perfect / n, 1),
        "avg_ms": round(total_ms / n),
        "counts": counts,
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate DEXI LLM GGUF models")
    parser.add_argument("--model", action="append", required=True,
                        help="Path to GGUF model (can specify multiple times)")
    parser.add_argument("--dataset", type=str, default=None,
                        help="Path to evaluation dataset (default: training/dataset/val.jsonl)")
    parser.add_argument("--limit", type=int, default=0,
                        help="Limit number of examples (0 = all)")
    args = parser.parse_args()

    dataset_path = args.dataset or str(DATASET_DIR / "val.jsonl")

    # Load examples
    print(f"Loading dataset: {dataset_path}")
    examples = []
    with open(dataset_path) as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))

    if args.limit > 0:
        examples = examples[:args.limit]
    print(f"  {len(examples)} examples loaded")

    system_block = load_system_block()

    # Evaluate each model
    all_summaries = []
    for model_path in args.model:
        if not Path(model_path).exists():
            print(f"\nERROR: Model not found: {model_path}")
            sys.exit(1)
        results, total_ms = evaluate_model(model_path, examples, system_block)
        summary = print_summary(model_path, results, total_ms)
        all_summaries.append(summary)

    # Side-by-side comparison
    if len(all_summaries) > 1:
        print(f"\n{'='*70}")
        print("  COMPARISON")
        print(f"{'='*70}")
        header = f"  {'Metric':<20s}"
        for s in all_summaries:
            header += f" {s['model'][:25]:>25s}"
        print(header)
        print(f"  {'-'*20}" + f" {'-'*25}" * len(all_summaries))

        for metric, key in [
            ("Perfect match", "perfect_pct"),
            ("Avg latency (ms)", "avg_ms"),
        ]:
            row = f"  {metric:<20s}"
            for s in all_summaries:
                val = s[key]
                row += f" {str(val) + ('%' if 'pct' in key else 'ms'):>25s}"
            print(row)

        for metric_name, count_key in [
            ("Tool call", "has_tool_call"),
            ("Correct tool", "correct_tool"),
            ("Correct endpoint", "correct_endpoint"),
            ("Correct args", "correct_args"),
        ]:
            row = f"  {metric_name:<20s}"
            for s in all_summaries:
                n = s["n"]
                c = s["counts"][count_key]
                row += f" {c}/{n} ({100*c/n:.1f}%)".rjust(25)
            print(row)

    print("\nDone!")


if __name__ == "__main__":
    main()
