# Helper Scripts

Scripts to manage rosbridge and other services.

## Rosbridge Management

### Start Rosbridge (Interactive)
```bash
~/scripts/start_rosbridge.sh
```

Starts rosbridge with workspace support:
- Sources ROS2 workspace (includes px4_msgs)
- Prompts to build if workspace is not built
- Provides detailed status information

### Start Rosbridge (Non-Interactive)
```bash
~/scripts/start_rosbridge_auto.sh
```

Automated startup (no prompts):
- Sources workspace if available
- Continues with warnings if not built
- Suitable for scripts/automation

### Stop Rosbridge
```bash
~/scripts/stop_rosbridge.sh
```

Stops the rosbridge server.

## Monitoring

### Check if Rosbridge is Running
```bash
pgrep -f rosbridge_websocket
```

### View Rosbridge Logs
```bash
tail -f /tmp/rosbridge.log
```

## Important Notes

- **Workspace Required**: Rosbridge needs the ROS2 workspace sourced to handle px4_msgs
- **First Time**: Run `~/dexi_ws/setup.sh` before starting rosbridge
- **WebSocket URLs**:
  - From host: `ws://localhost:9090`
  - From containers: `ws://ros2-dev:9090` or `ws://172.20.0.2:9090`

## Troubleshooting

### Rosbridge fails with "Unknown message type"
The workspace isn't sourced. Run:
```bash
cd ~/ros2_ws
./setup.sh
~/scripts/start_rosbridge.sh
```

### Rosbridge won't start
Check logs:
```bash
cat /tmp/rosbridge.log
```
