#!/bin/bash
# The bar counter (dexi_vision, 2 Hz) against the DEXI Lab bridge stickers, flown inside the ROS container.
ROS=$(docker ps -q --filter label=com.docker.compose.service=ros2-dev --filter publish=9090 | head -1)   # the stack behind :9090, not another one on the same host
[ -n "$ROS" ] || { echo "FAIL bars: no ros2-dev container"; exit 1; }
docker cp "$(dirname "$0")/bars.py" "$ROS":/tmp/release_bars.py
OUT=$(docker exec "$ROS" bash -c "source /opt/ros/jazzy/setup.bash; source /home/ubuntu/dexi_ws/install/setup.bash; timeout 240 python3 -u /tmp/release_bars.py 0.6 2>&1")
echo "$OUT" | tail -8
echo "$OUT" | grep -q "BARS: 4/4" && echo "PASS bars (bridge 1-3, no read on a barrel)" || { echo "FAIL bars"; exit 1; }
