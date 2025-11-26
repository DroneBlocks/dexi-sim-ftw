# Helper Scripts

Scripts to manage DEXI bringup and services.

## DEXI Bringup Management

### Stop DEXI Bringup
```bash
~/scripts/stop_dexi_bringup.sh
```

Stops all DEXI services including:
- LED Visualization Bridge
- PX4 Offboard Manager
- Rosbridge WebSocket
- ROS API

### Start DEXI Bringup
DEXI bringup starts automatically when you run:
```bash
cd ~/dexi_ws
./setup.sh
```

Or to restart manually after stopping:
```bash
~/scripts/stop_dexi_bringup.sh
cd ~/dexi_ws
./setup.sh
```

## Monitoring

### Check if DEXI Bringup is Running
```bash
ps aux | grep "ros2 launch dexi_bringup"
ros2 node list | grep dexi
```

### View DEXI Bringup Logs
```bash
tail -f ~/dexi_bringup.log
```

### Check ROS Topics
```bash
ros2 topic list | grep dexi
ros2 topic echo /dexi/led_visualization
```

## Important Notes

- **Automatic Startup**: DEXI bringup starts automatically via `setup.sh` or container restart
- **WebSocket URLs**:
  - From host: `ws://localhost:9090`
  - From containers: `ws://ros2-dev:9090` or `ws://172.20.0.2:9090`
- **LED Services**: Available at `/dexi/led_service/set_led_ring_color`, etc.

## Troubleshooting

### DEXI bringup not running
Check if workspace is built:
```bash
cd ~/dexi_ws
./setup.sh
```

### Services not available
Check logs and node status:
```bash
tail -f ~/dexi_bringup.log
ros2 node list
ros2 service list | grep dexi
```
