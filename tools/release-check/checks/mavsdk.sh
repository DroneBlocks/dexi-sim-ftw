#!/bin/bash
# The MAVSDK curriculum path: takeoff_and_land.py from dexi-mavsdk, run where code-server runs,
# over mavlink-router's 14540 feed.
ROS=$(docker ps -q --filter label=com.docker.compose.service=ros2-dev | head -1)
[ -n "$ROS" ] || { echo "FAIL mavsdk — no ros2-dev container"; exit 1; }
OUT=$(docker exec "$ROS" bash -c 'cd /home/ubuntu/dexi-mavsdk/missions 2>/dev/null || { echo "dexi-mavsdk missions not mounted"; exit 1; }; timeout 150 python3 -u takeoff_and_land.py 2>&1')
echo "$OUT" | tail -8
if echo "$OUT" | grep -qi "land"; then
  if echo "$OUT" | grep -qi "error\|Traceback\|timed out\|failed"; then echo "FAIL mavsdk takeoff_and_land"; exit 1; fi
  echo "PASS mavsdk takeoff_and_land"; else echo "FAIL mavsdk takeoff_and_land (never reached land)"; exit 1; fi
