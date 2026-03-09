# dexi_llm

ROS 2 node that runs a fine-tuned LLM on-device (Raspberry Pi 5) for natural language drone control. Translates voice/text commands into ROS 2 tool calls — flight, LEDs, telemetry, servos, GPIO, and more.

## How It Works

1. User sends a prompt (topic or service)
2. LLM generates `<tool_call>` tags with the correct ROS 2 service/topic calls
3. Node executes the tools and returns a response

The model is fine-tuned (QLoRA) on ~850 examples so a 1B parameter model reliably produces the exact service names, types, and arguments for ~20 ROS 2 interfaces.

## Quick Start (Pi)

```bash
# Requires: llama-cpp-python, dexi_interfaces, dexi_offboard
ros2 launch dexi_llm llm_node.launch.py \
  backend:=llama_cpp \
  model_path:=/path/to/dexi-llama-3.2-1b-q4_k_m.gguf \
  model_name:=llama-3.2-1b \
  n_threads:=4
```

## Interfaces

| Interface | Name | Type |
|-----------|------|------|
| Subscribe | `/dexi/llm/prompt` | `std_msgs/String` |
| Publish | `/dexi/llm/response` | `std_msgs/String` |
| Service | `/dexi/llm/llm_node/chat` | `dexi_interfaces/srv/LLMChat` |

## Supported Models

| Model | GGUF Size | Cold Start (Pi 5) | Warm Call |
|-------|-----------|-------------------|----------|
| `llama-3.2-1b` | ~0.7 GB | ~56s | ~10s |
| `qwen2.5-1.5b` | ~1.0 GB | TBD | TBD |
| `llama-3.2-3b` | ~2.0 GB | TBD | TBD |

## Launch Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `backend` | `keyword` | `keyword` (regex fallback) or `llama_cpp` |
| `model_path` | | Path to GGUF file |
| `model_name` | `qwen2.5-1.5b` | Config key in `config/models.json` |
| `n_ctx` | `2048` | Context window size |
| `n_threads` | `4` | CPU threads for inference |

## Training

See [training/README.md](training/README.md) for fine-tuning instructions.
