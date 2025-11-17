#!/bin/bash
set -e

echo "=== ROS2-DEV Container Starting ==="

# Source ROS2
source /opt/ros/jazzy/setup.bash

# Check if workspace is built
if [ -f ~/dexi_ws/install/setup.bash ]; then
    echo "✓ Workspace found, sourcing..."
    source ~/dexi_ws/install/setup.bash
else
    echo "⚠ Workspace not built yet"
    echo "  Build with: cd ~/dexi_ws && ./setup_jazzy.sh"
fi

# Auto-start rosbridge if workspace is ready
if [ -f ~/dexi_ws/install/setup.bash ]; then
    echo "Starting rosbridge automatically..."
    nohup ros2 launch rosbridge_server rosbridge_websocket_launch.xml > /tmp/rosbridge.log 2>&1 &

    # Wait a moment and check if it started
    sleep 3
    if pgrep -f "rosbridge_websocket" > /dev/null; then
        echo "✓ Rosbridge started automatically"
        echo "  WebSocket: ws://localhost:9090"
        echo "  Log file: /tmp/rosbridge.log"
    else
        echo "✗ Rosbridge failed to auto-start"
        echo "  Check logs: cat /tmp/rosbridge.log"
    fi
else
    echo "⚠ Skipping rosbridge auto-start (workspace not built)"
fi

echo "=== ROS2-DEV Ready ==="
echo ""

# Keep container running
exec "$@"
