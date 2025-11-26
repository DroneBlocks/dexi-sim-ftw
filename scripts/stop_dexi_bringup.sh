#!/bin/bash

echo "Stopping DEXI bringup..."

# Kill the launch file process
sudo pkill -f "ros2 launch dexi_bringup dexi_bringup_unity_sim"

# Also kill any related ROS nodes
sudo pkill -f "led_visualization_bridge"
sudo pkill -f "px4_offboard_manager"
sudo pkill -f "rosbridge_websocket"
sudo pkill -f "rosapi_node"

echo "DEXI bringup stopped."
