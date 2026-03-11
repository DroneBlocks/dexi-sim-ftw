#!/bin/bash

# Wait for container to fully start
sleep 10

# If workspace isn't built but we have a pre-built stash, populate it.
# This handles cloud deployments where host bind mounts shadow the image contents.
if [ ! -f /home/ubuntu/dexi_ws/install/setup.bash ] && [ -d /opt/dexi_ws_prebuilt/install ]; then
    echo "Populating workspace from pre-built image..."
    cp -a /opt/dexi_ws_prebuilt/install /home/ubuntu/dexi_ws/
    cp -a /opt/dexi_ws_prebuilt/build /home/ubuntu/dexi_ws/
    cp -a /opt/dexi_ws_prebuilt/log /home/ubuntu/dexi_ws/ 2>/dev/null || true
    # Copy any src packages that were cloned by vcs import (not in the host repo)
    for pkg in /opt/dexi_ws_prebuilt/src/*/; do
        pkg_name=$(basename "$pkg")
        if [ ! -d "/home/ubuntu/dexi_ws/src/$pkg_name" ]; then
            echo "  Copying missing package: $pkg_name"
            cp -a "$pkg" "/home/ubuntu/dexi_ws/src/$pkg_name"
        fi
    done
    echo "Workspace populated successfully."
fi

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
