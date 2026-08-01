# DEXI Drone Simulation (SITL)

Complete PX4 drone simulation with Unity 3D city, ROS2, Node-RED, and web-based ground control station.

## Prerequisites

- **Docker Desktop** installed and running
  - **Windows**: Install [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/) with the **WSL 2 backend** enabled (default on modern installs). Make sure WSL 2 is installed — Docker Desktop will prompt you if it isn't.
  - **Mac**: Install [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/).
  - **Linux**: Install [Docker Engine](https://docs.docker.com/engine/install/) or Docker Desktop.
- **Git** installed ([git-scm.com](https://git-scm.com/) — Windows users: use the default settings, the included `.gitattributes` handles line endings automatically)

## Quick Start

```bash
# 1. Clone repository
git clone --recursive https://github.com/DroneBlocks/dexi-sim-ftw.git
cd dexi-sim-ftw

# 2. Start all services (pulls pre-built images from Docker Hub)
docker compose up -d
```

**That's it!** The pre-built images include a compiled ROS2 workspace. On first start, the ros2-dev container automatically populates the workspace and launches rosbridge + DEXI bringup. Give it about 30 seconds after `docker compose up -d` for everything to initialize.

> **Windows note:** Port 80 (Ground Control) may conflict with IIS or other services. If `localhost` doesn't load, check that nothing else is using port 80, or change the port mapping in `docker-compose.yml` (e.g., `"8080:3000"`).

## Access Your Simulation

| Service | URL | Description |
|---------|-----|-------------|
| **Unity City** | http://localhost:1337 | 3D drone simulation |
| **Ground Control** | http://localhost | Web-based GCS |
| **Node-RED** | http://localhost:1880 | Visual programming |
| **Code Server** | https://localhost:9999 | Browser-based VS Code (password: `droneblocks`) |
| **VNC Desktop** | http://localhost:6080 | ROS2 development environment |

## What's Running

- **PX4 SITL** - Drone flight controller simulator
- **Unity City** - 3D environment visualization
- **ROS2 Humble** - Robot middleware with PX4 topics
- **Rosbridge** - WebSocket bridge for web apps (ws://localhost:9090)
- **Node-RED** - Flow-based drone programming
- **Web GCS** - Browser-based ground control station
- **Code Server** - VS Code in the browser with MAVSDK + Python for drone scripting

## Verify Everything Works

```bash
# Check ROS2 topics from PX4
docker compose exec ros2-dev bash -c "source ~/dexi_ws/install/setup.bash && ros2 topic list | grep fmu"

# View drone position
docker compose exec ros2-dev bash -c "source ~/dexi_ws/install/setup.bash && ros2 topic echo /fmu/out/vehicle_local_position"
```

You should see PX4 topics streaming data.

## Architecture

```
Unity Sim (1337) ─┐
Web GCS (80) ─────┼──> Rosbridge (9090) ──> ROS2 ──> PX4 SITL
Node-RED (1880) ──┘                         Topics    Simulator
Code Server (9999)
```

## Troubleshooting

### Rosbridge Not Starting?

The workspace auto-populates from the pre-built image on first run. Check the bringup log:
```bash
docker compose exec ros2-dev bash -c "tail -f ~/dexi_bringup.log"
```

You should see: `Rosbridge WebSocket server started on port 9090`

If the workspace wasn't populated (e.g., you built the image locally instead of pulling), you can build it manually:
```bash
# In VNC (http://localhost:6080):
cd ~/dexi_ws
./setup.sh
```

### Build Fails with `error: option --editable not recognized`

Symptom: `colcon build` fails on `dexi_led`, and everything that depends on it
(`dexi_offboard`, `dexi_ctf`, `dexi_apriltag`, `apriltag_ros`) is reported as aborted.

```
error: option --editable not recognized
Failed   <<< dexi_led [3.97s, exited with code 1]
```

setuptools 80 removed the `setup.py develop` command that `colcon build --symlink-install`
uses to build every Python package. If your container has setuptools 80 or newer, every
Python package in the workspace fails.

`./setup.sh` now detects this and pins setuptools back automatically, so the fix is to
build with it rather than calling `colcon build` directly:

```bash
docker compose exec ros2-dev bash -c "cd /home/ubuntu/dexi_ws && ./setup.sh"
```

To fix it by hand instead:

```bash
docker compose exec ros2-dev pip3 install "setuptools<80"
```

Images built from this repo pin `setuptools<80`, so this only affects containers created
from an older image. `docker compose pull` picks up the fixed one.

### Harmless Warnings You Can Ignore

These show up in a healthy build:

- `UserWarning: Unknown distribution option: 'tests_require'` is cosmetic setuptools noise.
- `WARNING:colcon...px4_msgs...are being used from /opt/px4_ws/install/px4_msgs` is correct.
  `px4_msgs` is pre-built in the base image on purpose so you don't recompile it.

A build is healthy when the summary line reports `0 packages failed`.

### Node-RED Permission Error? (Linux only)

```bash
sudo chown -R 1000:1000 ./node-red-dexi/flows
docker compose restart node-red
```

### Fresh Start

```bash
docker compose down
docker compose up -d
```

### Windows: Port 80 Conflict

If `http://localhost` doesn't load the Ground Control dashboard, another service may be using port 80. Edit `docker-compose.yml` and change `"80:3000"` to `"8080:3000"`, then access at `http://localhost:8080`.

## Development

### Where Things Live Inside the Container

The ROS2 workspace is at **`/home/ubuntu/dexi_ws`**. That is the container side of the
`./dexi_ws` bind mount in `docker-compose.yml`, so edits on your host show up instantly
inside the container and vice versa.

`docker compose exec ros2-dev bash` logs you in as **root**, not `ubuntu`. The VNC
desktop entrypoint needs root to start. The VNC session at http://localhost:6080 runs as
the `ubuntu` user. Both users now see the workspace at `~/dexi_ws`, because root's home
carries symlinks to the real paths:

| Inside the container | Real path | Host path |
|---|---|---|
| `~/dexi_ws` | `/home/ubuntu/dexi_ws` | `./dexi_ws` |
| `~/scripts` | `/home/ubuntu/scripts` | `./scripts` |
| `~/dexi-mavsdk` | `/home/ubuntu/dexi-mavsdk` | `./dexi-mavsdk` |

There is no `dexi` user and no `/root/dexi_ws` directory. If you see that path referenced
anywhere, it's the Raspberry Pi setup (`docker-compose.pi.yml`), which is a different image.

### Rebuilding the Workspace

**ROS2 Packages**: Add to `./dexi_ws/src/` and rebuild with `setup.sh`:
```bash
docker compose exec ros2-dev bash -c "cd /home/ubuntu/dexi_ws && ./setup.sh"
```

Use `setup.sh` rather than a bare `colcon build`. It pulls the external dependencies
listed in `dexi.repos`, builds the same package list CI builds, and skips the packages
that only compile on real drone hardware. A bare `colcon build` tries to build everything
in `src/`, including hardware-only packages like `dexi_cpp` and `dexi_camera`, and fails.

To rebuild a single package you're actively editing:
```bash
docker compose exec ros2-dev bash -c \
  "source /opt/ros/humble/setup.bash && cd /home/ubuntu/dexi_ws && \
   colcon build --packages-select dexi_led --symlink-install && \
   source install/setup.bash"
```

`--symlink-install` means edits to Python files take effect on node restart with no
rebuild. You only need to rebuild after changing `setup.py`, adding a new node, or
touching anything C++.

**View Logs**:
```bash
docker compose logs -f              # All services
docker compose logs -f ros2-dev     # Specific service
```

**Connect to Container**:
```bash
docker compose exec ros2-dev bash
```

## Multi-Architecture Support

All Docker images support both **amd64** (Intel/AMD) and **arm64** (Apple Silicon, Raspberry Pi):
- Works on x86 Linux/Windows PCs
- Works on Apple M1/M2/M3 Macs
- Works on ARM-based cloud instances

## Hardware Deployment

See [README.pi.md](README.pi.md) for deploying to real DEXI drones with Raspberry Pi.

---

**Need Help?** Open an issue at https://github.com/DroneBlocks/dexi-sim-ftw/issues
