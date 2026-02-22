"""Shared configuration for training and runtime.

Provides the single source of truth for tool definitions, system prompt,
and model-specific config (chat templates, stop tokens, LoRA params) so
that the fine-tuned model sees identical context at both training time
and inference time.
"""

import json
from pathlib import Path

_CONFIG_DIR = Path(__file__).parent


def load_tools() -> list[dict]:
    """Load tool definitions from tools.json."""
    with open(_CONFIG_DIR / "tools.json") as f:
        return json.load(f)


def load_system_prompt() -> str:
    """Load the system prompt from system_prompt.txt."""
    return (_CONFIG_DIR / "system_prompt.txt").read_text().strip()


def load_models() -> dict:
    """Load all model configurations from models.json."""
    with open(_CONFIG_DIR / "models.json") as f:
        return json.load(f)


def load_model_config(model_name: str) -> dict:
    """Load configuration for a specific model.

    Raises:
        KeyError: If model_name is not found in models.json.
    """
    models = load_models()
    if model_name not in models:
        available = ", ".join(sorted(models.keys()))
        raise KeyError(
            f"Unknown model '{model_name}'. Available: {available}"
        )
    return models[model_name]


def build_system_block(system_prompt: str, tools: list[dict]) -> str:
    """Build the model-agnostic system block with tools.

    Constructs the system prompt content that goes between the chat
    template's system_prefix and system_suffix. This is the same for
    all models — only the wrapping tokens differ.
    """
    tools_json = "\n".join(
        json.dumps(t, separators=(",", ":")) for t in tools
    )
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
