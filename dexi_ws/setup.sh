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

# setuptools 80 dropped `setup.py develop`, which --symlink-install needs below.
# The images pin setuptools<80, but repair older images and stray upgrades here.
SETUPTOOLS_MAJOR=$(python3 -c 'import setuptools; print(setuptools.__version__.split(".")[0])' 2>/dev/null || echo 0)
case "$SETUPTOOLS_MAJOR" in
    ''|*[!0-9]*) SETUPTOOLS_MAJOR=0 ;;
esac
if [ "$SETUPTOOLS_MAJOR" -ge 80 ]; then
    echo "setuptools $SETUPTOOLS_MAJOR.x dropped 'setup.py develop', which colcon --symlink-install needs."
    echo "Pinning setuptools below 80 before building..."
    if [ "$(id -u)" -eq 0 ]; then
        pip3 install --quiet "setuptools<80"
    else
        pip3 install --quiet --user "setuptools<80"
    fi
    echo "setuptools is now $(python3 -c 'import setuptools; print(setuptools.__version__)')"
fi

# Source ROS2 and pre-built px4_msgs from base image
source /opt/ros/humble/setup.bash
if [ -f "/opt/px4_ws/install/setup.bash" ]; then
    source /opt/px4_ws/install/setup.bash
    echo "Using pre-built px4_msgs from base image"
fi

# A workspace built before cv_bridge joined the list leaves a CMake cache in
# build/dexi_apriltag that keeps failing on the missing cv_bridge.hpp even after
# cv_bridge is built. Drop those artifacts so CMake reconfigures against it.
if [ ! -d "install/cv_bridge" ] && [ -d "build/dexi_apriltag" ]; then
    echo "Clearing stale dexi_apriltag artifacts (workspace predates the cv_bridge fix)..."
    rm -rf build/dexi_apriltag install/dexi_apriltag
fi

# Build only DEXI packages and required dependencies (px4_msgs is pre-built in base image)
# Keep this list in sync with ros2-dev/Dockerfile.sim, which is what CI builds.
# cv_bridge must be built, not ignored: dexi_apriltag needs cv_bridge.hpp, which
# the apt ros-humble-cv-bridge package does not ship.
echo "Building DEXI packages: dexi_interfaces, dexi_offboard, dexi_led, dexi_bringup, dexi_ctf, apriltag packages, cv_bridge..."
colcon build --packages-select dexi_interfaces dexi_offboard dexi_led dexi_bringup dexi_ctf \
    apriltag apriltag_msgs apriltag_ros dexi_apriltag \
    cv_bridge dexi_llm dexi_color_detection \
  --packages-ignore dexi_cpp dexi_camera dexi_yolo camera_ros \
    compressed_depth_image_transport compressed_image_transport \
    theora_image_transport zstd_image_transport image_transport_plugins \
  --symlink-install

# Source the workspace
source install/setup.bash

# Add auto-sourcing to .bashrc if not already present
if ! grep -q "source ~/dexi_ws/install/setup.bash" ~/.bashrc 2>/dev/null; then
    echo "" >> ~/.bashrc
    echo "# Auto-source ROS2 workspace" >> ~/.bashrc
    echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
    echo "if [ -f /opt/px4_ws/install/setup.bash ]; then source /opt/px4_ws/install/setup.bash; fi" >> ~/.bashrc
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
    nohup bash -c "source /opt/ros/humble/setup.bash && source /opt/px4_ws/install/setup.bash && source ~/dexi_ws/install/setup.bash && ros2 launch dexi_bringup dexi_bringup_unity_sim.launch.py" > ~/dexi_bringup.log 2>&1 &
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
