#!/bin/bash
# The v0.23 services end to end: /dexi/telemetry publishes, then the AprilTag example
# hops from tag 0 to tag 1 on /dexi/flight/command and /dexi/tag_nav/command.
ROS=$(docker ps -q --filter label=com.docker.compose.service=ros2-dev | head -1)
[ -n "$ROS" ] || { echo "FAIL tag-hop: no ros2-dev container"; exit 1; }
docker exec "$ROS" bash -c '
source /opt/ros/jazzy/setup.bash; source /home/ubuntu/dexi_ws/install/setup.bash
ros2 service type /dexi/flight/command | grep -q FlightCommand || { echo "FAIL /dexi/flight/command missing"; exit 1; }
ros2 service type /dexi/tag_nav/command | grep -q TagNavCommand || { echo "FAIL /dexi/tag_nav/command missing"; exit 1; }
timeout 10 ros2 topic echo --once /dexi/telemetry std_msgs/msg/String | grep -q "\"v\":1" || { echo "FAIL /dexi/telemetry not publishing"; exit 1; }
echo "PASS services and telemetry"
for d in /home/ubuntu/dexi_ws/src /opt/dexi_ws_prebuilt/src; do
  f=$d/dexi_apriltag/examples/python/hop_to_next_tag.py; [ -f $f ] && break
done
[ -f "$f" ] || { echo "FAIL hop_to_next_tag.py not found"; exit 1; }
timeout 180 python3 -u $f 2>&1 | tail -10
' ; rc=${PIPESTATUS[0]}
[ $rc -eq 0 ] && echo "PASS tag hop" || echo "FAIL tag hop"
exit $rc
