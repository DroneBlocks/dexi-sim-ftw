# DEXI Pi Setup

Docker Compose setup for Raspberry Pi with containerized ROS2 (headless).

**Note**: This uses `docker-compose.pi.yml` - includes a lightweight ROS2 Jazzy container without VNC for Pi deployments. For the full desktop development setup (with VNC), see [README.md](README.md).

## Architecture

```
┌─────────────────────────────────────────┐
│  Host Network Containers                 │
│                                          │
│  ros2-dev (host network)                 │
│  ├─ ROS2 Jazzy (headless, no VNC)        │
│  ├─ Rosbridge WebSocket (9090)           │
│  └─ Receives PX4 topics via DDS          │
│            ▲                             │
│            │ DDS (UDPv4)                  │
│            ▼                             │
│  px4-sitl (host network)                 │
│  ├─ PX4 SITL simulation                  │
│  └─ Connects to micro-dds on :8888       │
│            ▲                             │
│            │                             │
│  micro-dds-agent (host network)          │
│  └─ Bridges PX4 ↔ ROS2 via DDS           │
└─────────────────────────────────────────┘
            │
            │ WebSocket (9090)
            ▼
┌─────────────────────────────────────────┐
│  Bridge Network Containers               │
│                                          │
│  web-dashboard (80)                      │
│  node-red (1880)                         │
│  unity-sim (1337)                        │
│  └─ Connect to rosbridge via host.docker.internal:9090
└─────────────────────────────────────────┘
```

## Prerequisites

**On your Raspberry Pi:**

- Docker and Docker Compose installed
- Git installed

```bash
# Install Docker (if not already installed)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Enable Docker to start on boot
sudo systemctl enable docker

# Log out and back in for group changes to take effect

# Verify Docker
docker --version
docker compose version
```

## Quick Start

### 1. Clone Repository

```bash
cd ~
git clone https://github.com/DroneBlocks/dexi-sim-ftw.git
cd dexi-sim-ftw
```

### 2. Build and Start Containers

```bash
# Build images (first time only)
docker compose -f docker-compose.pi.yml build

# Start all services in background
docker compose -f docker-compose.pi.yml up -d

# View logs
docker compose -f docker-compose.pi.yml logs -f
```

This starts:
- **ros2-dev**: ROS2 Jazzy headless container (host network)
- **px4-sitl**: PX4 SITL simulation (host network)
- **micro-dds-agent**: Bridges PX4 to ROS2 via DDS (host network, jazzy version)
- **web-dashboard**: Port 80 (bridge network)
- **node-red**: Port 1880 (bridge network)
- **unity-sim**: Port 1337 (bridge network)

### 3. Setup ROS2 Workspace (First Time Only)

Enter the ros2-dev container and build the workspace:

```bash
# Enter ros2-dev container
docker compose -f docker-compose.pi.yml exec ros2-dev bash

# Inside container:
cd ~/dexi_ws
./setup_jazzy.sh
```

### 4. Verify Auto-Start

The ros2-dev container automatically starts rosbridge on boot (if workspace is built). Check the logs:

```bash
docker compose -f docker-compose.pi.yml logs ros2-dev
```

You should see "✓ Rosbridge started automatically"

### 5. Verify PX4 Topics

Inside the ros2-dev container:

```bash
source /opt/ros/jazzy/setup.bash
source ~/dexi_ws/install/setup.bash

# List PX4 topics
ros2 topic list | grep fmu

# Check topic data
ros2 topic hz /fmu/out/sensor_combined
ros2 topic echo /fmu/out/vehicle_status_v1
```

## Access Services

| Service | URL | Notes |
|---------|-----|-------|
| Web Dashboard | http://pi-ip-address | DEXI control interface |
| Node-RED | http://pi-ip-address:1880 | Flow-based programming |
| Unity Sim | http://pi-ip-address:1337 | City simulation |
| Rosbridge | ws://pi-ip-address:9090 | Running in ros2-dev container |
| ROS2 CLI | docker exec into ros2-dev | Headless, no VNC |

## Auto-Start on Reboot

All containers are configured with `restart: unless-stopped`:
- Containers automatically restart on Pi reboot
- Containers restart if they crash
- Rosbridge auto-starts when ros2-dev container starts (if workspace is built)

**After Pi reboot, everything should come up automatically:**

1. Docker daemon starts
2. All containers restart
3. PX4 SITL starts
4. Micro-DDS agent connects to PX4
5. ROS2-dev container starts and launches rosbridge
6. Web dashboard, Node-RED, and Unity connect to rosbridge

**To check status after reboot:**

```bash
# Check all containers are running
docker compose -f docker-compose.pi.yml ps

# Check rosbridge started
docker compose -f docker-compose.pi.yml logs ros2-dev | grep rosbridge
```

**To stop containers from auto-starting:**

```bash
docker compose -f docker-compose.pi.yml down
```

## Configuration Notes

### Network Configuration

**Host Network (DDS services):**
- `ros2-dev`, `px4-sitl`, `micro-dds-agent` use `network_mode: host`
- Allows direct DDS communication between containers
- Shares Pi's network namespace for optimal performance

**Bridge Network (Web services):**
- `web-dashboard`, `node-red`, `unity-sim` use `dexi-network` bridge
- Isolated from host network for security
- Connect to rosbridge via `host.docker.internal:9090` using `extra_hosts` mapping

### DDS Transport Configuration

All DDS containers are configured to use **UDPv4 transport only**:
- Shared memory transport doesn't work reliably on Pi
- Environment variables: `FASTDDS_BUILTIN_TRANSPORTS=UDPv4`
- Ensures reliable data flow between containers

### Rosbridge Connection

Web containers use `host.docker.internal:9090` to reach rosbridge in ros2-dev container:
```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

This works on Docker 20.10+ on Linux. If you have issues, use your Pi's actual IP:
```yaml
environment:
  - ROSBRIDGE_URL=ws://192.168.1.100:9090
```

## Troubleshooting

### PX4 topics not appearing in ROS2

**Check micro-dds-agent logs:**
```bash
docker compose -f docker-compose.pi.yml logs micro-dds-agent
```

Look for successful RTPS connection and topic creation messages.

**Enter ros2-dev and check topics:**
```bash
docker compose -f docker-compose.pi.yml exec ros2-dev bash
source /opt/ros/jazzy/setup.bash
source ~/dexi_ws/install/setup.bash
ros2 topic list | grep fmu
```

### Workspace not built

If you see errors about px4_msgs not found:

```bash
docker compose -f docker-compose.pi.yml exec ros2-dev bash
cd ~/dexi_ws
./setup_jazzy.sh
```

### Rosbridge not running

Check if rosbridge is running:
```bash
docker compose -f docker-compose.pi.yml exec ros2-dev bash
pgrep -f rosbridge_websocket
```

If not, start it:
```bash
~/scripts/start_rosbridge_jazzy.sh
```

### Topics discovered but no data

This should NOT happen with the containerized setup since all DDS containers use UDPv4 transport. If it does:

1. **Check DDS environment:**
   ```bash
   docker compose -f docker-compose.pi.yml exec ros2-dev printenv | grep FASTDDS
   ```
   Should show: `FASTDDS_BUILTIN_TRANSPORTS=UDPv4`

2. **Restart containers:**
   ```bash
   docker compose -f docker-compose.pi.yml restart
   ```

### Web Dashboard/Node-RED can't connect to rosbridge

**Test rosbridge from Pi:**
```bash
# Install wscat if not present
sudo npm install -g wscat

# Test connection
wscat -c ws://localhost:9090
```

If this works but containers can't connect, update the compose file with your Pi's actual IP address.

### Unity simulation performance

Unity may be resource-intensive on Pi. If performance is poor:
- Reduce simulation quality settings
- Run Unity on a separate x86_64 machine and point it to your Pi's IP

## Development Workflow

### Adding ROS2 Packages

1. **Add packages to workspace:**
   ```bash
   # On Pi, edit files in ./dexi_ws/src/
   # Files are mounted into ros2-dev container
   ```

2. **Build inside container:**
   ```bash
   docker compose -f docker-compose.pi.yml exec ros2-dev bash
   cd ~/dexi_ws
   source /opt/ros/jazzy/setup.bash
   colcon build
   source install/setup.bash
   ```

3. **Restart rosbridge if you added new message types:**
   ```bash
   pkill -f rosbridge_websocket
   ~/scripts/start_rosbridge_jazzy.sh
   ```

### Accessing ROS2 CLI

```bash
# Enter ros2-dev container
docker compose -f docker-compose.pi.yml exec ros2-dev bash

# Source workspace
source /opt/ros/jazzy/setup.bash
source ~/dexi_ws/install/setup.bash

# Use ROS2 commands
ros2 topic list
ros2 node list
ros2 run your_package your_node
```

## Common Commands

All commands use the `-f docker-compose.pi.yml` flag to specify the Pi-specific compose file.

```bash
# Start services (foreground)
docker compose -f docker-compose.pi.yml up

# Start services (background/detached)
docker compose -f docker-compose.pi.yml up -d

# Stop all services
docker compose -f docker-compose.pi.yml down

# Restart all services
docker compose -f docker-compose.pi.yml restart

# Restart specific service
docker compose -f docker-compose.pi.yml restart px4-sitl

# View all logs
docker compose -f docker-compose.pi.yml logs -f

# View specific service logs
docker compose -f docker-compose.pi.yml logs -f micro-dds-agent

# List running services
docker compose -f docker-compose.pi.yml ps

# Enter a running container
docker compose -f docker-compose.pi.yml exec px4-sitl bash

# Pull latest images
docker compose -f docker-compose.pi.yml pull

# Remove stopped containers and networks
docker compose -f docker-compose.pi.yml down --remove-orphans
```

## Stopping Services

```bash
# Stop Docker containers (graceful shutdown)
docker compose -f docker-compose.pi.yml down

# Stop and remove volumes
docker compose -f docker-compose.pi.yml down -v

# Stop rosbridge (Ctrl+C in terminal, or if using systemd)
sudo systemctl stop rosbridge
```
