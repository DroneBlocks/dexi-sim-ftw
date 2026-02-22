#!/usr/bin/env python3
"""Generate a training dataset from seed examples.

Reads seed examples from seed_examples/*.jsonl, uses an LLM API to generate
natural language variations of the user prompts, and outputs a full training
dataset in the Qwen2.5 Hermes tool-calling format.

Usage:
    # Generate with Claude (default)
    python generate_dataset.py --api anthropic --variations 10

    # Generate with OpenAI-compatible API
    python generate_dataset.py --api openai --variations 10

    # Just combine seeds without expansion (no API needed)
    python generate_dataset.py --no-expand

Output: dataset/train.jsonl
"""

import argparse
import json
import random
import sys
from pathlib import Path

# Allow running from training/ directory without installing dexi_llm
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dexi_llm.config import load_tools

SEED_DIR = Path(__file__).parent / "seed_examples"
OUTPUT_DIR = Path(__file__).parent / "dataset"

VARIATION_PROMPT = """\
You are generating training data for a small drone assistant LLM.

Given a seed example of a user command and the expected assistant response (with tool calls), \
generate {n} diverse natural language variations of the USER message only. \
The assistant response and tool call should remain EXACTLY the same — only the user phrasing changes.

Keep variations:
- Natural and conversational (how real users would talk to a drone)
- Varied in style: casual, formal, brief, verbose, with/without please, etc.
- Include common misspellings or abbreviations where natural (e.g., "fwd" for forward)
- Include different ways to express the same number (e.g., "2 meters", "2m", "two meters")
- Some should be commands, some questions, some requests

Seed user message: "{user_msg}"
Tool call that should be made: {tool_call_summary}

Return ONLY a JSON array of strings, one per variation. No other text.
"""


def load_seeds() -> list[dict]:
    """Load all seed examples from JSONL files."""
    seeds = []
    for jsonl_file in sorted(SEED_DIR.glob("*.jsonl")):
        with open(jsonl_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    seeds.append(json.loads(line))
    return seeds


def extract_tool_summary(assistant_msg: str) -> str:
    """Extract a brief summary of the tool call from assistant message."""
    import re
    match = re.search(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", assistant_msg, re.DOTALL)
    if match:
        try:
            tc = json.loads(match.group(1))
            name = tc.get("name", "")
            args = tc.get("arguments", {})
            return f"{name}({json.dumps(args)})"
        except json.JSONDecodeError:
            pass
    return "no tool call"


def format_training_example(messages: list[dict], tools: list[dict]) -> dict:
    """Format a single training example in Qwen2.5 Hermes format."""
    return {
        "messages": messages,
        "tools": tools,
    }


def generate_variations_anthropic(
    user_msg: str, tool_summary: str, n: int, model: str = "claude-sonnet-4-20250514"
) -> list[str]:
    """Generate variations using Anthropic API."""
    try:
        import anthropic
    except ImportError:
        print("pip install anthropic", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic()
    prompt = VARIATION_PROMPT.format(
        n=n, user_msg=user_msg, tool_call_summary=tool_summary
    )

    response = client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    # Parse JSON array from response
    try:
        variations = json.loads(text)
        if isinstance(variations, list):
            return [v for v in variations if isinstance(v, str)]
    except json.JSONDecodeError:
        # Try to extract JSON array from markdown code block
        import re
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    print(f"  Warning: failed to parse variations for: {user_msg[:50]}", file=sys.stderr)
    return []


def generate_variations_openai(
    user_msg: str, tool_summary: str, n: int, model: str = "gpt-4o-mini"
) -> list[str]:
    """Generate variations using OpenAI-compatible API."""
    try:
        import openai
    except ImportError:
        print("pip install openai", file=sys.stderr)
        sys.exit(1)

    client = openai.OpenAI()
    prompt = VARIATION_PROMPT.format(
        n=n, user_msg=user_msg, tool_call_summary=tool_summary
    )

    response = client.chat.completions.create(
        model=model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.choices[0].message.content.strip()
    try:
        variations = json.loads(text)
        if isinstance(variations, list):
            return [v for v in variations if isinstance(v, str)]
    except json.JSONDecodeError:
        import re
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    print(f"  Warning: failed to parse variations for: {user_msg[:50]}", file=sys.stderr)
    return []


def main():
    parser = argparse.ArgumentParser(description="Generate training dataset from seeds")
    parser.add_argument(
        "--api", choices=["anthropic", "openai"], default="anthropic",
        help="Which LLM API to use for generating variations",
    )
    parser.add_argument(
        "--variations", type=int, default=10,
        help="Number of variations to generate per seed example",
    )
    parser.add_argument(
        "--no-expand", action="store_true",
        help="Just combine seeds without generating variations (no API needed)",
    )
    parser.add_argument(
        "--model", type=str, default=None,
        help="Override the model to use (default: claude-sonnet-4-20250514 / gpt-4o-mini)",
    )
    args = parser.parse_args()

    # Load data
    seeds = load_seeds()
    tools = load_tools()

    print(f"Loaded {len(seeds)} seed examples")

    # Build dataset
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    dataset = []

    # Always include original seeds
    for seed in seeds:
        example = format_training_example(seed["messages"], tools)
        dataset.append(example)

    if not args.no_expand:
        # Generate variations
        generate_fn = (
            generate_variations_anthropic if args.api == "anthropic"
            else generate_variations_openai
        )
        model = args.model or (
            "claude-sonnet-4-20250514" if args.api == "anthropic" else "gpt-4o-mini"
        )

        for i, seed in enumerate(seeds):
            user_msg = seed["messages"][0]["content"]  # First message is user
            assistant_msg = seed["messages"][-1]["content"]  # Last message is assistant
            tool_summary = extract_tool_summary(assistant_msg)

            # Skip refusals/info that have no tool call — vary those less
            category = seed.get("category", "")
            n = args.variations if category not in ("refusal", "info") else max(3, args.variations // 3)

            print(f"[{i+1}/{len(seeds)}] Generating {n} variations for: {user_msg[:60]}...")
            variations = generate_fn(user_msg, tool_summary, n, model=model)

            for var_msg in variations:
                # Replace user message, keep assistant response identical
                var_messages = [{"role": "user", "content": var_msg}] + seed["messages"][1:]
                example = format_training_example(var_messages, tools)
                dataset.append(example)

            print(f"  -> {len(variations)} variations generated")

    # Shuffle
    random.seed(42)
    random.shuffle(dataset)

    # Split train/val (90/10)
    split_idx = int(len(dataset) * 0.9)
    train_data = dataset[:split_idx]
    val_data = dataset[split_idx:]

    # Write output
    train_path = OUTPUT_DIR / "train.jsonl"
    val_path = OUTPUT_DIR / "val.jsonl"

    with open(train_path, "w") as f:
        for example in train_data:
            f.write(json.dumps(example) + "\n")

    with open(val_path, "w") as f:
        for example in val_data:
            f.write(json.dumps(example) + "\n")

    print(f"\nDataset generated:")
    print(f"  Seeds:      {len(seeds)}")
    print(f"  Total:      {len(dataset)}")
    print(f"  Train:      {len(train_data)} -> {train_path}")
    print(f"  Validation: {len(val_data)} -> {val_path}")


if __name__ == "__main__":
    main()
