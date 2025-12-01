# DEXI Drone Simulation (SITL)

Complete PX4 drone simulation with Unity 3D city, ROS2, Node-RED, and web-based ground control station.

## Quick Start

```bash
# 1. Clone repository
git clone --recursive https://github.com/DroneBlocks/dexi-sim-ftw.git
cd dexi-sim-ftw

# 2. Fix permissions (if on Linux/DigitalOcean as root)
sudo chown -R 1000:1000 ./node-red-dexi/flows

# 3. Start all services
docker compose up -d

# 4. Build ROS2 workspace (first time only)
# Open browser to http://localhost:6080 (VNC desktop)
# In VNC terminal:
cd ~/dexi_ws
./setup.sh
```

**That's it!** All services are now running (setup.sh automatically starts rosbridge and DEXI bringup).

## Access Your Simulation

| Service | URL | Description |
|---------|-----|-------------|
| **Unity City** | http://localhost:1337 | 3D drone simulation |
| **Ground Control** | http://localhost | Web-based GCS |
| **Node-RED** | http://localhost:1880 | Visual programming |
| **VNC Desktop** | http://localhost:6080 | ROS2 development environment |

## What's Running

- **PX4 SITL** - Drone flight controller simulator
- **Unity City** - 3D environment visualization
- **ROS2 Humble** - Robot middleware with PX4 topics
- **Rosbridge** - WebSocket bridge for web apps (ws://localhost:9090)
- **Node-RED** - Flow-based drone programming
- **Web GCS** - Browser-based ground control station

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
```

## Troubleshooting

### Rosbridge Not Working?

Make sure you built the workspace:
```bash
# In VNC (http://localhost:6080):
cd ~/dexi_ws
./setup.sh

# Check if it's running:
docker compose exec ros2-dev bash -c "tail -f ~/dexi_bringup.log"
```

You should see: `Rosbridge WebSocket server started on port 9090`

### Node-RED Permission Error?

```bash
sudo chown -R 1000:1000 ./node-red-dexi/flows
docker compose restart node-red
```

### Fresh Start

```bash
docker compose down
docker compose up -d
```

## Development

**ROS2 Packages**: Add to `./dexi_ws/src/` and rebuild:
```bash
# In VNC:
cd ~/dexi_ws
colcon build
source install/setup.bash
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
- Works on x86 Linux servers
- Works on Apple M1/M2/M3 Macs
- Works on ARM-based cloud instances

## For CTF/Educational Use

Check out [CHALLENGE_IDEAS.md](../dexi-ctf/CHALLENGE_IDEAS.md) for 30+ drone programming challenges, from beginner to expert level.

## Hardware Deployment

See [README.pi.md](README.pi.md) for deploying to real DEXI drones with Raspberry Pi.

---

**Need Help?** Open an issue at https://github.com/DroneBlocks/dexi-sim-ftw/issues
