#!/bin/bash
set -e

echo "=== ROS2 Workspace Setup ==="

# Get the script directory and navigate to workspace root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Import dependencies from dexi.repos
if [ -f "src/dexi_bringup/dexi.repos" ]; then
    echo "Importing dependencies from dexi.repos..."
    vcs import src < src/dexi_bringup/dexi.repos
else
    echo "Warning: dexi.repos not found at src/dexi_bringup/dexi.repos"
fi

# Source ROS2
source /opt/ros/humble/setup.bash

# Build only DEXI packages (dependencies will be built automatically)
echo "Building DEXI packages: dexi_bringup, dexi_interfaces, dexi_offboard..."
colcon build --packages-up-to dexi_bringup dexi_interfaces dexi_offboard

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
echo "To start rosbridge, restart the container:"
echo "  docker compose restart ros2-dev"
echo ""
echo "Rosbridge will then be available at ws://localhost:9090"
echo ""
echo "To use the workspace in THIS terminal, run:"
echo "  source ~/dexi_ws/install/setup.bash"
echo ""
echo "Or close and open a new terminal (auto-sourcing is enabled)."
echo ""
echo "Test it with:"
echo "  ros2 topic list | grep fmu"
echo "  ros2 topic echo /fmu/out/vehicle_status_v1"
