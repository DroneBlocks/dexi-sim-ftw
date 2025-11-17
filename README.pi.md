# DEXI Pi Setup

Docker Compose setup for Raspberry Pi with native ROS2 installation.

**Note**: This uses `docker-compose.pi.yml` - a simplified setup for Pi that assumes you have ROS2 Humble running natively on your Pi host. For the full desktop development setup (with VNC), see [README.md](README.md).

## Architecture

```
┌─────────────────────────────────────────┐
│  Raspberry Pi Host                       │
│  - ROS2 Humble (native)                  │
│  - Rosbridge WebSocket (9090)            │
│  - DDS Domain (receives PX4 topics)      │
└─────────────────────────────────────────┘
            ▲
            │ DDS + WebSocket
            │
┌───────────┴─────────────────────────────┐
│  Docker Containers                       │
│                                          │
│  px4-sitl (host network)                 │
│  ├─ PX4 SITL simulation                  │
│  └─ Connects to micro-dds on :8888       │
│                                          │
│  micro-dds-agent (host network)          │
│  └─ Bridges PX4 ↔ Host ROS2 via DDS      │
│                                          │
│  web-dashboard (bridge network)          │
│  node-red (bridge network)               │
│  unity-sim (bridge network)              │
│  └─ Connect to rosbridge on host         │
└──────────────────────────────────────────┘
```

## Prerequisites

**On your Raspberry Pi host:**

```bash
# ROS2 Humble must be installed
source /opt/ros/humble/setup.bash

# Install rosbridge server
sudo apt install ros-humble-rosbridge-server

# Install px4_msgs (required for rosbridge to handle PX4 topics)
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src
git clone https://github.com/PX4/px4_msgs.git -b release/1.16
cd ~/ros2_ws
colcon build
source install/setup.bash
```

## Quick Start

### 1. Start Rosbridge on Pi Host

In a terminal on your Pi:

```bash
# Source ROS2 and your workspace
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash

# Start rosbridge
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
```

This exposes ROS2 topics via WebSocket on port 9090.

### 2. Start Docker Containers

In another terminal on your Pi:

```bash
# Navigate to the project directory
cd /path/to/dexi_unity_sitl_dev

# Build images (first time only, or after changes)
docker compose -f docker-compose.pi.yml build

# Start all services (foreground, see logs)
docker compose -f docker-compose.pi.yml up

# OR start in background (detached mode)
docker compose -f docker-compose.pi.yml up -d

# View logs (if running in background)
docker compose -f docker-compose.pi.yml logs -f

# View logs for specific service
docker compose -f docker-compose.pi.yml logs -f px4-sitl
```

This starts:
- **px4-sitl**: PX4 SITL simulation (host network) with 127.0.0.1 arguments
- **micro-dds-agent**: Bridges PX4 to host ROS2 via DDS (host network)
- **web-dashboard**: Port 80
- **node-red**: Port 1880
- **unity-sim**: Port 1337

### 3. Verify PX4 Topics on Host

In another terminal on your Pi:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash

# List PX4 topics
ros2 topic list | grep fmu

# Echo vehicle status
ros2 topic echo /fmu/out/vehicle_status_v1

# Echo local position
ros2 topic echo /fmu/out/vehicle_local_position
```

## Access Services

| Service | URL | Notes |
|---------|-----|-------|
| Web Dashboard | http://pi-ip-address | DEXI control interface |
| Node-RED | http://pi-ip-address:1880 | Flow-based programming |
| Unity Sim | http://pi-ip-address:1337 | City simulation |
| Rosbridge | ws://pi-ip-address:9090 | Running on host (not in container) |

## Configuration Notes

### Host Network Mode

PX4 SITL and micro-dds-agent use `network_mode: host` to:
- Allow PX4 to connect to micro-dds-agent on localhost:8888
- Allow micro-dds-agent to publish DDS topics to host ROS2
- Simplify DDS discovery between containers and host

### Rosbridge Connection

The web containers connect to rosbridge on the host using `host.docker.internal:9090`.

**Note**: On Linux, `host.docker.internal` may not work by default. If you have connection issues:

1. **Option A**: Use your Pi's actual IP address in the compose file:
   ```yaml
   environment:
     - ROSBRIDGE_URL=ws://192.168.1.100:9090  # Your Pi's IP
   ```

2. **Option B**: Add extra_hosts to each service:
   ```yaml
   extra_hosts:
     - "host.docker.internal:host-gateway"
   ```

### Node-RED Rosbridge Configuration

In Node-RED, configure the rosbridge-websocket node to connect to:
- `ws://host.docker.internal:9090` (or your Pi's IP)

## Troubleshooting

### PX4 topics not appearing in host ROS2

**Check micro-dds-agent logs:**
```bash
docker compose -f docker-compose.pi.yml logs micro-dds-agent
```

Look for successful RTPS connection messages.

**Verify DDS_DOMAIN_ID matches:**
```bash
# On host, check domain (default is 0)
echo $ROS_DOMAIN_ID
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

## Auto-starting Rosbridge

To auto-start rosbridge on boot, create a systemd service:

```bash
sudo nano /etc/systemd/system/rosbridge.service
```

```ini
[Unit]
Description=ROS2 Rosbridge WebSocket Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi
Environment="ROS_DOMAIN_ID=0"
ExecStart=/bin/bash -c "source /opt/ros/humble/setup.bash && source /home/pi/ros2_ws/install/setup.bash && ros2 launch rosbridge_server rosbridge_websocket_launch.xml"
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable rosbridge
sudo systemctl start rosbridge
sudo systemctl status rosbridge
```

## Development Workflow

1. **ROS2 packages**: Develop on host in `~/ros2_ws/src/`
2. **Build**: `cd ~/ros2_ws && colcon build`
3. **Restart rosbridge**: If you add new message types

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
