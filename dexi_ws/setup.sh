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

# Build only DEXI packages and required dependencies
echo "Building DEXI packages: px4_msgs, dexi_interfaces, dexi_offboard, dexi_led, dexi_bringup, apriltag packages..."
colcon build --packages-select px4_msgs dexi_interfaces dexi_offboard dexi_led dexi_bringup \
    apriltag apriltag_msgs apriltag_ros dexi_apriltag \
  --packages-ignore dexi_cpp dexi_camera dexi_yolo camera_ros \
    compressed_depth_image_transport compressed_image_transport \
    theora_image_transport zstd_image_transport image_transport_plugins cv_bridge \
  --symlink-install

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

# Check if DEXI bringup is already running
if pgrep -f "ros2 launch dexi_bringup dexi_bringup_unity_sim" > /dev/null; then
    echo "DEXI bringup is already running. Skipping startup."
    echo "To restart, run: ~/scripts/stop_dexi_bringup.sh && cd ~/dexi_ws && ./setup.sh"
else
    echo "Starting DEXI bringup in background..."
    nohup bash -c "source /opt/ros/humble/setup.bash && source ~/dexi_ws/install/setup.bash && ros2 launch dexi_bringup dexi_bringup_unity_sim.launch.py" > ~/dexi_bringup.log 2>&1 &
    echo "DEXI bringup started! Logs available at ~/dexi_bringup.log"
fi
echo ""
echo "Rosbridge is now available at ws://localhost:9090"
echo ""
echo "To view logs:"
echo "  tail -f ~/dexi_bringup.log"
echo ""
echo "Test it with:"
echo "  ros2 topic list | grep fmu"
echo "  ros2 topic echo /fmu/out/vehicle_status_v1"
