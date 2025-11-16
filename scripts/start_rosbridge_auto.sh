#!/bin/bash
# Non-interactive version for automated startup

echo "Starting Rosbridge Server (auto mode)..."

# Source ROS2
source /opt/ros/humble/setup.bash

# Check if workspace exists and source it
if [ -f ~/dexi_ws/install/setup.bash ]; then
    echo "Sourcing ROS2 workspace..."
    source ~/dexi_ws/install/setup.bash
    echo "✓ Workspace sourced (px4_msgs available)"
else
    echo "⚠ Warning: Workspace not built - px4_msgs may not be available"
    echo "  Run: cd ~/dexi_ws && ./setup.sh"
fi

# Check if rosbridge is already running
if pgrep -f "rosbridge_websocket" > /dev/null; then
    echo "Rosbridge is already running"
    exit 0
fi

# Start rosbridge in the background
echo "Launching rosbridge..."
nohup ros2 launch rosbridge_server rosbridge_websocket_launch.xml > /tmp/rosbridge.log 2>&1 &

sleep 3

if pgrep -f "rosbridge_websocket" > /dev/null; then
    echo "✓ Rosbridge started on ws://ros2-dev:9090"
else
    echo "✗ Failed to start Rosbridge - check /tmp/rosbridge.log"
    exit 1
fi
