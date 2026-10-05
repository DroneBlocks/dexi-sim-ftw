#!/bin/bash
ROS=$(docker ps -q --filter label=com.docker.compose.service=ros2-dev | head -1)
[ -n "$ROS" ] || { echo "FAIL regressions — no ros2-dev container"; exit 1; }
docker cp "$(dirname "$0")/regressions.py" "$ROS":/tmp/release_regressions.py
docker exec "$ROS" bash -c 'source /opt/ros/jazzy/setup.bash 2>/dev/null || source /opt/ros/humble/setup.bash; source /home/ubuntu/dexi_ws/install/setup.bash; timeout 240 python3 -u /tmp/release_regressions.py 2>&1' | tail -14
exit ${PIPESTATUS[0]}
