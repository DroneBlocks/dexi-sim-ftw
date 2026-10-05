#!/bin/bash
# The color detection node against the DEXI Lab color pads, flown inside the ROS container.
ROS=$(docker ps -q --filter label=com.docker.compose.service=ros2-dev | head -1)
[ -n "$ROS" ] || { echo "FAIL color — no ros2-dev container"; exit 1; }
docker cp "$(dirname "$0")/color.py" "$ROS":/tmp/release_color.py
OUT=$(docker exec "$ROS" bash -c 'source /opt/ros/jazzy/setup.bash 2>/dev/null || source /opt/ros/humble/setup.bash; source /home/ubuntu/dexi_ws/install/setup.bash; timeout 200 python3 -u /tmp/release_color.py 2>&1')
echo "$OUT" | tail -8
echo "$OUT" | grep -q "COLOR DETECTION: PASS" && echo "PASS color detection (5 pads)" || { echo "FAIL color detection"; exit 1; }
