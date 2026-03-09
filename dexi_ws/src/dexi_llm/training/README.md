# DEXI LLM Training Pipeline

Fine-tune small instruct models for reliable drone tool-calling using QLoRA + Unsloth.

## Why Fine-Tune?

Small instruct models (1-3B) support tool calling but are unreliable at this scale — succeeding ~60-70% of the time. Fine-tuning on our narrow domain (~20 ROS2 services) teaches the model to reliably produce the exact `<tool_call>` format with correct service names, types, and arguments. A fine-tuned 1.5B model can exceed a general-purpose 7B model on this specific task while running at 10-15 tokens/sec on a Raspberry Pi 5.

## Supported Models

| Model | Base | VRAM | GGUF Size | Notes |
|-------|------|------|-----------|-------|
| `qwen2.5-1.5b` | Qwen2.5-1.5B-Instruct | ~4 GB | ~1 GB | Default, proven on Pi 5 |
| `llama-3.2-1b` | Llama-3.2-1B-Instruct | ~3 GB | ~0.7 GB | Smallest, fastest inference |
| `llama-3.2-3b` | Llama-3.2-3B-Instruct | ~5 GB | ~2 GB | Best quality, needs more VRAM |

## Quick Start (Local NVIDIA GPU)

> **Windows users:** Unsloth and CUDA training do **not** work natively on Windows.
> You must use **WSL 2** (Windows Subsystem for Linux). See [Windows (WSL 2)](#windows-wsl-2) below before proceeding.

### 1. Set up venv

```bash
cd dexi_ws/src/dexi_llm
python3 -m venv venv
source venv/bin/activate
pip install -r training/requirements.txt
```

### 2. Train

```bash
# Default (Qwen 2.5 1.5B)
python training/train_local.py

# Llama 3.2 1B
python training/train_local.py --model llama-3.2-1b

# Llama 3.2 3B with custom settings
python training/train_local.py --model llama-3.2-3b --epochs 5 --batch-size 4
```

Training takes ~20-30 min on an RTX GPU. The script will:
- Load the base model in 4-bit
- Add LoRA adapters
- Train for 3 epochs (default)
- Test on 8 sample prompts
- Export to GGUF Q4_K_M

### 3. Deploy

```bash
# Copy GGUF into models directory
cp dexi-qwen2.5-1.5b-gguf/*.gguf models/dexi-qwen2.5-1.5b-q4_k_m.gguf

# Or SCP to Pi
scp dexi-qwen2.5-1.5b-gguf/*.gguf dexi@192.168.68.59:~/dexi_ws/src/dexi_llm/models/dexi-qwen2.5-1.5b-q4_k_m.gguf

# Launch
ros2 launch dexi_llm llm_node.launch.py backend:=llama_cpp \
    model_path:=/path/to/dexi-qwen2.5-1.5b-q4_k_m.gguf
```

### 4. Test

Open the web dashboard chat page and toggle to **Local LLM**. Try:
- "make the led green" → should call `/dexi/led_service/set_led_ring_color`
- "fly forward 2 meters" → should call `/dexi/execute_blockly_command`
- "what's my battery?" → should subscribe to `/fmu/out/battery_status`
- "play some music" → should politely refuse

## Google Colab (Alternative)

If you don't have a local NVIDIA GPU, use the Colab notebook (Qwen 2.5 only):

1. Upload `training/dexi_finetune.ipynb` to [colab.research.google.com](https://colab.research.google.com/) and set **T4 GPU** runtime
2. Upload data files when prompted:
   - From `training/dataset/`: `train.jsonl`, `val.jsonl`
   - From `dexi_llm/config/`: `tools.json`, `system_prompt.txt`, `models.json`
3. Run all cells (~20-30 min)
4. Download the GGUF file and deploy as above

## Windows (WSL 2)

Unsloth requires a Linux environment with native CUDA support. On Windows, use WSL 2 — your host NVIDIA GPU is automatically passed through.

### Prerequisites

1. **NVIDIA GPU driver** installed on Windows (the host driver is shared with WSL — do **not** install a separate Linux driver)
2. **WSL 2** enabled:
   ```powershell
   wsl --install -d Ubuntu-24.04
   ```
3. Verify GPU access inside WSL:
   ```bash
   nvidia-smi
   ```
   You should see your GPU listed. If not, update your NVIDIA driver and ensure WSL 2 (not WSL 1) is active.

### Setup inside WSL

```bash
# Install Python and venv
sudo apt update && sudo apt install -y python3 python3-venv python3-pip

# Clone or navigate to the repo (use /mnt/c/ to access Windows files,
# but training is faster on the native Linux filesystem)
git clone <your-repo-url> ~/dexi-sim-ftw
cd ~/dexi-sim-ftw/dexi_ws/src/dexi_llm

# Create venv and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r training/requirements.txt

# Train
python training/train_local.py
```

> **Tip:** Training on the Linux filesystem (`~/`) is significantly faster than on `/mnt/c/` due to filesystem overhead. Clone the repo inside WSL for best performance, then copy the GGUF output back to Windows or directly to the Pi.

### Copy GGUF out of WSL

```bash
# From WSL to Windows
cp dexi-qwen2.5-1.5b-gguf/*.gguf /mnt/c/Users/<you>/dexi-qwen2.5-1.5b-q4_k_m.gguf

# Or directly to Pi
scp dexi-qwen2.5-1.5b-gguf/*.gguf dexi@192.168.68.59:~/dexi_ws/src/dexi_llm/models/
```

## Directory Structure

```
dexi_llm/
├── config/                            # Shared config (single source of truth)
│   ├── __init__.py                    # load_tools(), load_system_prompt(), load_model_config(), build_system_block()
│   ├── tools.json                     # 4 tool definitions (used by training + runtime)
│   ├── system_prompt.txt              # System prompt (used by training + runtime)
│   └── models.json                    # Model config: chat template, stop tokens, LoRA params
├── system_prompt.py                   # SYSTEM_PROMPT = load_system_prompt()
├── ros_tools.py                       # TOOL_DEFINITIONS = load_tools()
└── ...

training/
├── train_local.py            # Local GPU training script (--model flag)
├── requirements.txt          # Python dependencies (just unsloth)
├── dexi_finetune.ipynb       # Google Colab notebook (Qwen only)
├── capabilities.json         # Machine-readable capability metadata (valid values, ranges)
├── seed_examples/            # Hand-written seed examples per category (~5-10 each)
│   ├── flight.jsonl          # 26 seeds: takeoff, land, fly 6 dirs, yaw, box, arm/disarm
│   ├── led.jsonl             # 19 seeds: ring color (17 colors), pixel color, effects
│   ├── telemetry.jsonl       # 14 seeds: battery, altitude, position, status, YOLO, topics
│   ├── hardware.jsonl        # 14 seeds: servos, GPIO, flips (4 dirs), camera recording
│   └── refusals.jsonl        # 10 seeds: out-of-scope, help, greetings, safety limits
├── generate_dataset.py       # (Optional) Expand seeds → full dataset via LLM API
├── dataset/                  # Pre-generated training data (ready to use)
│   ├── train.jsonl           # 765 examples
│   └── val.jsonl             # 85 examples
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
5. Re-train: `python training/train_local.py --model <your-model>` (~30 min)
6. Deploy new GGUF

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
