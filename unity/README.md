# Unity Sim Environments

Each subfolder contains a self-contained Unity WebGL sim with its own Dockerfile, nginx config, and build artifacts.

## Sims

| Sim | Image | Description |
|-----|-------|-------------|
| `dexi-sim` | `droneblocks/dexi-sitl-city` | Standard DEXI city environment |
| `avr-2025-sim` | `droneblocks/avr-2025-sim` | AVR 2025 competition environment |

## Directory Structure

```
unity/
├── avr-2025-sim/
│   ├── Build/          # Unity WebGL build artifacts
│   ├── index.html      # UI with rosbridge, virtual joystick, keyboard controls
│   ├── Dockerfile
│   └── nginx.conf
└── dexi-sim/
    ├── Build/
    ├── index.html
    ├── Dockerfile
    └── nginx.conf
```

## Building

All builds use `unity/` as the Docker context with each sim's Dockerfile.

### Local build (current platform)

```bash
# AVR 2025 sim
docker build -f unity/avr-2025-sim/Dockerfile -t droneblocks/avr-2025-sim:latest unity/

# Standard DEXI sim
docker build -f unity/dexi-sim/Dockerfile -t droneblocks/dexi-sitl-city:latest unity/
```

### Multi-arch build and push

```bash
docker buildx build --platform linux/amd64,linux/arm64 \
  -f unity/avr-2025-sim/Dockerfile \
  -t droneblocks/avr-2025-sim:latest \
  --push unity/

docker buildx build --platform linux/amd64,linux/arm64 \
  -f unity/dexi-sim/Dockerfile \
  -t droneblocks/dexi-sitl-city:latest \
  --push unity/
```

## Running

```bash
docker run -d --restart=unless-stopped -p 1337:1337 droneblocks/avr-2025-sim:latest
```

Access at `http://localhost:1337`
