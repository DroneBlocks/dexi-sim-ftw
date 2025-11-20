# DEXI Unity SITL Development

Modular Docker Compose setup for PX4 SITL simulation with ROS2, web dashboard, and Node-RED.

**Raspberry Pi Users**: See [README.pi.md](README.pi.md) for a simplified setup that uses native ROS2 on your Pi.

## Architecture

```
┌─────────────────────────────────────────┐
│  ros2-dev (172.20.0.2)                  │
│  - ROS2 Humble + VNC (6080)             │
│  - Rosbridge WebSocket (9090) ←─────────┼─── web-dashboard (80)
│  - PX4 topics via micro-dds             │    ├─── node-red (1880)
└─────────────────────────────────────────┘    └─── unity-sim (1337)
            │
            │ DDS Bridge
            ▼
┌─────────────────────────────────────────┐
│  px4-sitl + micro-dds-agent             │
│  - PX4 SITL headless simulation         │
│  - Micro-DDS agent (shares network)     │
└─────────────────────────────────────────┘
```

## Quick Start

```bash
# 1. Clone with submodules
git clone --recursive https://github.com/DroneBlocks/dexi-sim-ftw.git
cd dexi-sim-ftw

# Or if already cloned, initialize submodules:
git submodule update --init --recursive

# 2. Build and start
docker compose build
docker compose up

# 3. Setup ROS2 workspace (first time only)
# Open VNC: http://localhost:6080
# In terminal:
cd ~/dexi_ws
./setup.sh

# 4. Start rosbridge (required for dashboard & Node-RED)
~/scripts/start_rosbridge.sh
```

**Note**: The setup script (step 3) must be run before rosbridge, as rosbridge needs px4_msgs and other dependencies.

## Troubleshooting

### Node-RED Permission Issues

If Node-RED fails to start with a permission error (`EACCES: permission denied, mkdir '/data/node_modules'`), fix the permissions on the flows directory:

```bash
# Set correct ownership for Node-RED data directory
sudo chown -R 1000:1000 ./node-red-dexi/flows

# Restart Node-RED
docker compose restart node-red
```

The Node-RED container runs as user ID 1000, so the mounted directory must be owned by that user.

## Access Services

| Service | URL (from host) | URL (from containers) | Description |
|---------|-----------------|----------------------|-------------|
| **VNC Desktop** | http://localhost:6080 | - | ROS2 Humble desktop environment |
| **Web Dashboard** | http://localhost | - | DEXI DroneBlocks control interface |
| **Node-RED** | http://localhost:1880 | - | Flow-based programming |
| **Unity Sim** | http://localhost:1337 | - | DEXI Unity city simulation |
| **Rosbridge** | ws://localhost:9090 | ws://ros2-dev:9090 or ws://172.20.0.2:9090 | ROS2 WebSocket bridge |

**Important**: In Node-RED and Web Dashboard, use `ws://ros2-dev:9090` for rosbridge connection.

## Verify PX4 Connection

```bash
# List PX4 topics
ros2 topic list | grep fmu

# View vehicle status
ros2 topic echo /fmu/out/vehicle_status_v1

# View position
ros2 topic echo /fmu/out/vehicle_local_position
```

## Development

- **ROS2 Workspace**: `./dexi_ws` (persistent, mounted volume)
- **Add packages**: Place in `./dexi_ws/src/` and run `colcon build`
- **Scripts**: Helper scripts in `./scripts`
- **Details**: See `./dexi_ws/README.md`

## Common Commands

```bash
# View logs
docker compose logs -f

# Enter containers
docker compose exec ros2-dev bash
docker compose exec px4-sitl bash

# Stop/restart
docker compose down
docker compose restart ros2-dev

# Start rosbridge
docker compose exec ros2-dev bash -c "~/scripts/start_rosbridge.sh"
```

## Services

| Service | Image | Ports |
|---------|-------|-------|
| ros2-dev | Custom (./ros2-dev) | 6080, 9090 |
| px4-sitl | jonasvautherin/px4-gazebo-headless:1.16.0 | - |
| micro-dds-agent | microros/micro-ros-agent:humble | - |
| web-dashboard | droneblocks/dexi-droneblocks:latest | 80 |
| node-red | droneblocks/dexi-node-red:latest | 1880 |
| unity-sim | droneblocks/dexi-sitl-city:latest | 1337 |
