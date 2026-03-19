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
- **ROS2 Jazzy** - Robot middleware with PX4 topics
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

**ROS2 Packages**: Add to `./dexi_ws/src/` and rebuild:
```bash
# In VNC:
cd ~/dexi_ws
./setup.sh
```

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
