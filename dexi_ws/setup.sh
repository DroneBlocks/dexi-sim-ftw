#!/bin/bash
set -e

echo "=== ROS2 Workspace Setup ==="

# Clone px4_msgs if not present
if [ ! -d "src/px4_msgs" ]; then
    echo "Cloning px4_msgs..."
    cd src
    git clone https://github.com/PX4/px4_msgs.git -b release/1.16
    cd ..
else
    echo "px4_msgs already cloned"
fi

# Build workspace
echo "Building workspace..."
source /opt/ros/humble/setup.bash
colcon build

# Source the workspace
source install/setup.bash

# Add auto-sourcing to .bashrc if not already present
if ! grep -q "source ~/dexi_ws/install/setup.bash" ~/.bashrc 2>/dev/null; then
    echo "" >> ~/.bashrc
    echo "# Auto-source ROS2 workspace" >> ~/.bashrc
    echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
    echo "if [ -f ~/dexi_ws/install/setup.bash ]; then source ~/dexi_ws/install/setup.bash; fi" >> ~/.bashrc
    echo "Added auto-sourcing to ~/.bashrc"
fi

echo ""
echo "=== Setup Complete! ==="
echo "Workspace will be automatically sourced in new terminals."
echo ""
echo "Test it with:"
echo "  ros2 topic list | grep fmu"
echo "  ros2 topic echo /fmu/out/vehicle_status_v1"
