#!/bin/bash
# dexi_yolo (AVR 2026 model, 1 Hz) against the DEXI Lab stickers, flown inside the ROS container.
ROS=$(docker ps -q --filter label=com.docker.compose.service=ros2-dev | head -1)
[ -n "$ROS" ] || { echo "FAIL yolo: no ros2-dev container"; exit 1; }
docker cp "$(dirname "$0")/yolo.py" "$ROS":/tmp/release_yolo.py
STICKERS=wheat,water,gasoline,toxic,blackout,wheat_barn,water_barn,bridge_1
OUT=$(docker exec "$ROS" bash -c "source /opt/ros/jazzy/setup.bash; source /home/ubuntu/dexi_ws/install/setup.bash; timeout 330 python3 -u /tmp/release_yolo.py 0.6 $STICKERS 2>&1")
echo "$OUT" | tail -10
echo "$OUT" | grep -q "YOLO: 8/8 classes" && echo "PASS yolo (8 AVR 2026 classes)" || { echo "FAIL yolo"; exit 1; }
