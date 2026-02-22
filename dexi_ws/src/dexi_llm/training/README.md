# DEXI LLM Training Pipeline

Fine-tune a base model for reliable drone tool-calling using QLoRA + Unsloth.

**Supported models:** Qwen2.5-1.5B-Instruct (default), Llama 3.2-1B-Instruct. Model-specific config (chat templates, stop tokens, LoRA params) lives in `models.json` — the training notebook and runtime both read from it.

## Why Fine-Tune?

The base Qwen2.5-1.5B-Instruct model supports tool calling via `<tool_call>` XML tags, but at 1.5B parameters it's unreliable — sometimes it generates the correct XML format, sometimes it outputs raw Python-style text that the parser can't match. In testing, it succeeded ~60-70% of the time.

Fine-tuning on our specific drone commands (a narrow domain of ~20 services) teaches the model to reliably produce the exact `<tool_call>` format with correct service names, types, and arguments. A fine-tuned 1.5B model can exceed a general-purpose 7B model on this specific task while running at 10-15 tokens/sec on a Raspberry Pi 5.

## Quick Start

The training dataset (850 examples) is pre-generated. You only need a free Google Colab account — no API keys required.

### 1. Open Colab

Go to [colab.research.google.com](https://colab.research.google.com/), create a new notebook, and set **T4 GPU** (Runtime → Change runtime type → T4 GPU).

### 2. Upload the notebook cells

Copy the cells from `training/dexi_finetune.ipynb` into Colab (or upload the `.ipynb` file directly via File → Upload notebook).

### 3. Upload 5 config/data files

The upload cell opens two file dialogs (one per directory):

**Upload #1** — navigate to `training/dataset/`, select:
- `train.jsonl`
- `val.jsonl`

**Upload #2** — navigate to `dexi_llm/config/`, select:
- `tools.json`
- `system_prompt.txt`
- `models.json`

### 4. Select model

In the model selection cell, set `MODEL_NAME`:

```python
MODEL_NAME = "qwen2.5-1.5b"  # or "llama3.2-1b"
```

### 5. Run all cells

Run each cell in order. Training takes ~20-30 minutes on T4. The notebook will:
- Load the base model in 4-bit (~2GB VRAM)
- Add LoRA adapters (config-driven from `models.json`)
- Format the dataset with the model's chat template
- Train for 3 epochs
- Test on sample prompts
- Export to GGUF Q4_K_M
- Download the GGUF file

### 6. Deploy

#### Qwen (default)

```bash
# Copy GGUF into the models directory
cp ~/Downloads/unsloth.Q4_K_M.gguf dexi_ws/src/dexi_llm/models/dexi-qwen2.5-1.5b-q4_k_m.gguf

# Launch (model_name defaults to qwen2.5-1.5b)
ros2 launch dexi_llm llm_node.launch.py backend:=llama_cpp \
    model_path:=/path/to/dexi-qwen2.5-1.5b-q4_k_m.gguf
```

#### Llama

```bash
cp ~/Downloads/unsloth.Q4_K_M.gguf dexi_ws/src/dexi_llm/models/dexi-llama3.2-1b-q4_k_m.gguf

# Must pass model_name so runtime uses the correct chat template
ros2 launch dexi_llm llm_node.launch.py backend:=llama_cpp \
    model_path:=/path/to/dexi-llama3.2-1b-q4_k_m.gguf \
    model_name:=llama3.2-1b
```

#### To a Real Pi

```bash
scp ~/Downloads/unsloth.Q4_K_M.gguf dexi@192.168.68.59:~/dexi_ws/src/dexi_llm/models/<gguf_name>

# On the Pi:
ros2 launch dexi_llm llm_node.launch.py backend:=llama_cpp \
    model_path:=/home/dexi/dexi_ws/src/dexi_llm/models/<gguf_name> \
    model_name:=<qwen2.5-1.5b or llama3.2-1b>
```

### 7. Test

Open the web dashboard chat page and toggle to **Local LLM**. Try:
- "make the led green" → should call `/dexi/led_service/set_led_ring_color`
- "fly forward 2 meters" → should call `/dexi/execute_blockly_command`
- "what's my battery?" → should subscribe to `/fmu/out/battery_status`
- "play some music" → should politely refuse

## Multi-Model Architecture

The pipeline is **model-agnostic** — the dataset contains raw `{messages, tools}` with no chat template baked in. Model-specific wrapping happens at:

- **Training time**: The Colab notebook reads `models.json` to get the chat template tokens for the selected model and wraps each example accordingly.
- **Runtime**: `tool_executor.py` reads `models.json` to build prompts with the correct tokens and stop sequences.

The ONLY model-specific parts are:
- **Chat template tokens** (e.g. `<|im_start|>` for Qwen vs `<|start_header_id|>` for Llama)
- **Stop tokens** (e.g. `<|im_end|>` vs `<|eot_id|>`)
- **LoRA parameters** (can differ per model but currently identical)

Everything else — system prompt, tool definitions, `<tool_call>` XML format — is shared.

## Directory Structure

```
dexi_llm/
├── config/                            # SHARED config (single source of truth)
│   ├── __init__.py                    # load_tools(), load_system_prompt(), load_model_config(), build_system_block()
│   ├── tools.json                     # 4 tool definitions (used by training + runtime)
│   ├── system_prompt.txt              # System prompt (used by training + runtime)
│   └── models.json                    # Model registry: chat templates, stop tokens, LoRA params
├── system_prompt.py                   # SYSTEM_PROMPT = load_system_prompt()
├── ros_tools.py                       # TOOL_DEFINITIONS = load_tools()
└── ...

training/
├── dexi_finetune.ipynb        # Google Colab notebook (upload or copy cells)
├── capabilities.json          # Machine-readable capability metadata (valid values, ranges)
├── seed_examples/             # Hand-written seed examples per category (~5-10 each)
│   ├── flight.jsonl           # 26 seeds: takeoff, land, fly 6 dirs, yaw, box, arm/disarm
│   ├── led.jsonl              # 19 seeds: ring color (17 colors), pixel color, effects
│   ├── telemetry.jsonl        # 14 seeds: battery, altitude, position, status, YOLO, topics
│   ├── hardware.jsonl         # 14 seeds: servos, GPIO, flips (4 dirs), camera recording
│   └── refusals.jsonl         # 10 seeds: out-of-scope, help, greetings, safety limits
├── generate_dataset.py        # (Optional) Expand seeds → full dataset via LLM API
├── dataset/                   # Pre-generated training data (ready to use)
│   ├── train.jsonl            # 765 examples
│   └── val.jsonl              # 85 examples
└── README.md
```

## Capabilities Covered

| Category | Capabilities | Seeds | Examples |
|----------|-------------|-------|----------|
| **Flight** | takeoff, land, fly (6 dirs), yaw, box_mission, arm/disarm, stop | 26 | ~260 |
| **LED** | 17 ring colors, pixel RGB, 8 effects (galaxy, meteor, rainbow, comet, ripple, loading, blink) | 19 | ~190 |
| **Telemetry** | battery, altitude, position, GPS, armed status, YOLO detections, topic discovery | 14 | ~140 |
| **Hardware** | servo control (16ch), GPIO read/write, flips (4 dirs), video recording | 14 | ~140 |
| **Refusals/Info** | out-of-scope requests, help, greetings, safety bounds | 10 | ~37 |
| **Total** | | **83** | **850** |

## (Optional) Regenerate the Dataset

> **Skip this** if you just want to train — the dataset is already included.

The generation script reads each seed example and uses an LLM API to generate 10 natural language rephrasings of each user prompt. The assistant response (with tool calls) stays identical — only the user phrasing varies.

```bash
pip install anthropic

# Generate with Claude Haiku (fast, cheap)
export ANTHROPIC_API_KEY=sk-ant-...
python generate_dataset.py --api anthropic --variations 10 --model claude-haiku-4-5-20251001

# Or with OpenAI
pip install openai
export OPENAI_API_KEY=sk-...
python generate_dataset.py --api openai --variations 10

# Or just combine seeds without expansion (no API key needed)
python generate_dataset.py --no-expand
```

## Adding New Capabilities

When you add a new ROS2 package or service:

1. Update `dexi_llm/config/system_prompt.txt` (and optionally `training/capabilities.json`)
2. If the new capability needs a new tool type (unlikely), update `dexi_llm/config/tools.json`
3. Write 5-10 seed examples in a new or existing `.jsonl` file in `seed_examples/`
4. Re-run `python generate_dataset.py` to regenerate (requires API key)
5. Re-train on Colab (~30 min) — upload the updated config files alongside the dataset
6. Deploy new GGUF

## Adding New Models

Add an entry to `config/models.json` with:
- `base_model` — Unsloth/HuggingFace model name
- `chat_template` — bos, system/user/assistant prefix/suffix tokens
- `stop_tokens` — generation stop sequences
- `lora` — r, lora_alpha, target_modules, lora_dropout
- `training` — lora_dir, merged_dir, gguf_dir
- `gguf_name` — default output filename

No code changes needed. Set `MODEL_NAME` in the notebook and `model_name` at launch.

## Seed Example Format

Each `.jsonl` file in `seed_examples/` contains one example per line:

```json
{
  "messages": [
    {"role": "user", "content": "make the led green"},
    {"role": "assistant", "content": "Setting LEDs to green.\n\n<tool_call>\n{\"name\": \"call_service\", \"arguments\": {\"service\": \"/dexi/led_service/set_led_ring_color\", \"service_type\": \"dexi_interfaces/srv/LEDRingColor\", \"args\": {\"color\": \"green\"}}}\n</tool_call>"}
  ],
  "category": "led"
}
```

## Model Alternatives

| Model | Size (Q4) | Pi 5 Speed | Status |
|-------|-----------|-----------|--------|
| Qwen2.5-1.5B | ~1GB | ~10-15 tok/s | Supported (default) |
| Llama 3.2-1B | ~0.7GB | ~12-18 tok/s | Supported |
| Qwen3-1.7B | ~1.1GB | ~8-12 tok/s | Add to `models.json` |
| Qwen3-4B | ~2.5GB | ~3-5 tok/s | Add to `models.json` |
