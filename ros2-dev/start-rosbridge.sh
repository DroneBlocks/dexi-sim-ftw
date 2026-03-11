#!/bin/bash

# Wait for container to fully start
sleep 10

# Start rosbridge if workspace is built
if [ -f /home/ubuntu/dexi_ws/install/setup.bash ]; then
    echo "Starting rosbridge automatically..."
    source /opt/ros/humble/setup.bash
    source /home/ubuntu/dexi_ws/install/setup.bash
    exec ros2 launch rosbridge_server rosbridge_websocket_launch.xml
else
    echo "Workspace not built yet - rosbridge not started"
    echo "Run /home/ubuntu/dexi_ws/setup.sh inside VNC to build workspace and start rosbridge"
    # Keep process running so docker compose doesn't think it failed
    exec tail -f /dev/null
fi
