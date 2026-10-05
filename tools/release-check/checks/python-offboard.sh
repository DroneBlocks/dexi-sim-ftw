#!/bin/bash
# The rclpy tag-hop example, run inside the ROS container exactly as a student would from code-server.
ROS=$(docker ps -q --filter label=com.docker.compose.service=ros2-dev | head -1)
[ -n "$ROS" ] || { echo "FAIL python offboard: no ros2-dev container"; exit 1; }
OUT=$(docker exec "$ROS" bash -c 'source /opt/ros/jazzy/setup.bash 2>/dev/null || source /opt/ros/humble/setup.bash; source /home/ubuntu/dexi_ws/install/setup.bash
  for f in /home/ubuntu/dexi_ws/src/dexi_offboard/examples/python/apriltag_tag_hop.py /home/ubuntu/apriltag_tag_hop.py; do [ -f $f ] && { cd $(dirname $f); timeout 170 python3 -u $f --route 0 1 --takeoff 1.0 2>&1; exit; }; done
  echo "example apriltag_tag_hop.py not found"')
echo "$OUT" | tail -8
if echo "$OUT" | grep -q "✓ center_on_tag 1" && echo "$OUT" | grep -q "✓ land"; then echo "PASS python offboard (rclpy): tag 0 -> tag 1"; else echo "FAIL python offboard (rclpy)"; exit 1; fi
