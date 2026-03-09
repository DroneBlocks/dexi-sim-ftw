#!/usr/bin/env python3
"""Local validation for the Colab notebook — no GPU required.

Tests that dataset loading, formatting, and the formatting_func work correctly
in both single-example and batched modes (Unsloth calls both).

Run: python3 training/test_notebook_local.py
"""
import json
import sys
from pathlib import Path

TRAINING_DIR = Path(__file__).parent
CONFIG_DIR = TRAINING_DIR.parent / "dexi_llm" / "config"

# Load config (same as notebook)
with open(CONFIG_DIR / "models.json") as f:
    MODEL_CONFIG = json.load(f)["qwen2.5-1.5b"]
tpl = MODEL_CONFIG["chat_template"]

with open(CONFIG_DIR / "tools.json") as f:
    TOOLS = json.load(f)
with open(CONFIG_DIR / "system_prompt.txt") as f:
    SYSTEM_PROMPT = f.read().strip()

tools_json = "\n".join(json.dumps(t, separators=(",", ":")) for t in TOOLS)
SYSTEM_BLOCK = (
    f"{SYSTEM_PROMPT}\n\n"
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


# --- format_example (called by dataset.map, always single example) ---
def format_example(example):
    text = tpl["bos"]
    text += tpl["system_prefix"] + SYSTEM_BLOCK + tpl["system_suffix"]
    for msg in example["messages"]:
        role = msg["role"]
        if role == "user":
            text += tpl["user_prefix"] + msg["content"] + tpl["user_suffix"]
        elif role == "assistant":
            text += tpl["assistant_prefix"] + msg["content"] + tpl["assistant_suffix"]
    return {"text": text}


# --- formatting_func (trivial passthrough, called by Unsloth both ways) ---
def formatting_func(example):
    return example["text"]


# ========== TESTS ==========

errors = 0

# Load a sample from the dataset
with open(TRAINING_DIR / "dataset" / "train.jsonl") as f:
    sample_raw = json.loads(f.readline())

print("=== Test 1: format_example (single example) ===")
try:
    result = format_example(sample_raw)
    assert "text" in result, "Missing 'text' key"
    assert isinstance(result["text"], str), f"Expected str, got {type(result['text'])}"
    assert tpl["system_prefix"] in result["text"], "Missing system prefix"
    assert tpl["assistant_prefix"] in result["text"], "Missing assistant prefix"
    assert sample_raw["messages"][0]["content"] in result["text"], "Missing user content"
    print(f"  PASS — {len(result['text'])} chars")
except Exception as e:
    print(f"  FAIL — {e}")
    errors += 1

print("\n=== Test 2: formatting_func (single example, as Unsloth _tokenize calls it) ===")
try:
    formatted = format_example(sample_raw)
    single_example = {"text": formatted["text"], "messages": sample_raw["messages"]}
    result = formatting_func(single_example)
    assert isinstance(result, str), f"Expected str, got {type(result)}"
    print(f"  PASS — returns str ({len(result)} chars)")
except Exception as e:
    print(f"  FAIL — {e}")
    errors += 1

print("\n=== Test 3: formatting_func (batched, as SFTTrainer constructor may call it) ===")
try:
    # Simulate HF datasets batched format
    formatted1 = format_example(sample_raw)
    with open(TRAINING_DIR / "dataset" / "train.jsonl") as f:
        lines = [json.loads(line) for line in f.readlines()[:3]]
    batch = {"text": [format_example(ex)["text"] for ex in lines]}
    result = formatting_func(batch)
    assert isinstance(result, list), f"Expected list, got {type(result)}"
    assert len(result) == 3, f"Expected 3 items, got {len(result)}"
    assert all(isinstance(t, str) for t in result), "Not all items are strings"
    print(f"  PASS — returns list of {len(result)} strings")
except Exception as e:
    print(f"  FAIL — {e}")
    errors += 1

print("\n=== Test 4: ChatML structure ===")
try:
    result = format_example(sample_raw)["text"]
    # Check proper ChatML structure
    assert result.count("<|im_start|>system") == 1, "Should have exactly 1 system block"
    assert result.count("<|im_start|>user") == 1, "Should have exactly 1 user block"
    assert result.count("<|im_start|>assistant") == 1, "Should have exactly 1 assistant block"
    assert result.count("<|im_end|>") == 3, "Should have exactly 3 im_end tokens"
    # Check tool_call tags are preserved (supports multiple per assistant response)
    assistant_content = sample_raw["messages"][-1]["content"]
    src_count = assistant_content.count("<tool_call>")
    if src_count > 0:
        # Only count in the assistant portion (system block also contains <tool_call>)
        assistant_part = result.split(tpl["assistant_prefix"])[-1]
        fmt_count = assistant_part.count("<tool_call>")
        assert fmt_count == src_count, (
            f"Expected {src_count} tool_call(s) in assistant response, got {fmt_count}"
        )
    print(f"  PASS — valid ChatML structure (tool_calls: {src_count})")
except Exception as e:
    print(f"  FAIL — {e}")
    errors += 1

print("\n=== Test 5: All training examples format without error ===")
try:
    with open(TRAINING_DIR / "dataset" / "train.jsonl") as f:
        count = 0
        for line in f:
            ex = json.loads(line)
            result = format_example(ex)
            assert isinstance(result["text"], str)
            assert len(result["text"]) > 100
            count += 1
    print(f"  PASS — {count} examples formatted")
except Exception as e:
    print(f"  FAIL at example {count} — {e}")
    errors += 1

print(f"\n{'='*50}")
if errors == 0:
    print("All tests passed!")
else:
    print(f"{errors} test(s) FAILED")
    sys.exit(1)
