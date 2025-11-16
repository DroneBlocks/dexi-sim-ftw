#!/bin/bash
set -e

echo "Starting Rosbridge Server..."

# Source ROS2
source /opt/ros/humble/setup.bash

# Check if workspace exists and source it
if [ -f ~/dexi_ws/install/setup.bash ]; then
    echo "Sourcing ROS2 workspace..."
    source ~/dexi_ws/install/setup.bash
    echo "✓ Workspace sourced (px4_msgs available)"
elif [ -d ~/dexi_ws/src ] && [ ! -d ~/dexi_ws/install ]; then
    echo "⚠ Warning: Workspace not built!"
    echo "  Run: cd ~/dexi_ws && ./setup.sh"
    echo ""
    read -p "Build workspace now? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cd ~/dexi_ws
        ./setup.sh
        source ~/dexi_ws/install/setup.bash
    else
        echo "⚠ Continuing without workspace (px4_msgs may not be available)"
    fi
else
    echo "⚠ Warning: No workspace found at ~/dexi_ws"
    echo "  px4_msgs may not be available to rosbridge"
fi

# Check if rosbridge is already running
if pgrep -f "rosbridge_websocket" > /dev/null; then
    echo "Rosbridge is already running"
    echo "To stop it: pkill -f rosbridge_websocket"
    exit 0
fi

# Start rosbridge in the background
echo "Launching rosbridge..."
nohup ros2 launch rosbridge_server rosbridge_websocket_launch.xml > /tmp/rosbridge.log 2>&1 &

sleep 3

if pgrep -f "rosbridge_websocket" > /dev/null; then
    echo ""
    echo "✓ Rosbridge started successfully"
    echo "  WebSocket: ws://localhost:9090"
    echo "  From containers: ws://ros2-dev:9090"
    echo "  From host: ws://localhost:9090"
    echo "  Log file: /tmp/rosbridge.log"
    echo ""
    echo "Test with: tail -f /tmp/rosbridge.log"
else
    echo ""
    echo "✗ Failed to start Rosbridge"
    echo "  Check logs: cat /tmp/rosbridge.log"
    exit 1
fi
