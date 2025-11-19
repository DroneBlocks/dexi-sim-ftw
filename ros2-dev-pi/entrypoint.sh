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
    # Launch with explicit parameter types to fix Jazzy parameter type issue
    nohup ros2 run rosbridge_server rosbridge_websocket --ros-args \
        -p port:=9090 \
        -p address:='0.0.0.0' \
        -p delay_between_messages:=0.0 \
        -p max_message_size:=10000000 \
        -p unregister_timeout:=10.0 \
        > /tmp/rosbridge.log 2>&1 &

    # Wait a moment and check if it started
    sleep 3
    if pgrep -f "rosbridge_websocket" > /dev/null; then
        echo "✓ Rosbridge started automatically"
        echo "  WebSocket: ws://0.0.0.0:9090"
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
