#!/bin/bash

# Wait for container to fully start
sleep 10

# Start DEXI bringup if workspace is built
if [ -f /home/ubuntu/dexi_ws/install/setup.bash ]; then
    echo "Starting DEXI Unity Sim bringup..."
    source /opt/ros/humble/setup.bash
    source /home/ubuntu/dexi_ws/install/setup.bash
    exec ros2 launch dexi_bringup dexi_bringup_unity_sim.launch.py
else
    echo "Workspace not built yet - DEXI bringup not started"
    echo "Run /home/ubuntu/dexi_ws/setup.sh inside VNC to build workspace and start DEXI"
    # Keep process running so docker compose doesn't think it failed
    exec tail -f /dev/null
fi
