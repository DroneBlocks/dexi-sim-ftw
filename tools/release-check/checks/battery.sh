#!/bin/bash
# The sim skips PX4's battery health checks (CBRK_SUPPLY_CHK), because battery_simulator can
# stop publishing after a disarm and a stale battery blocks every arm (PX4 #27653).
PX4=$(docker ps -q --filter label=com.docker.compose.service=px4-sitl | head -1)
[ -n "$PX4" ] || { echo "FAIL battery: no px4-sitl container"; exit 1; }
for _ in $(seq 1 12); do
  v=$(docker exec "$PX4" /opt/px4/bin/px4-param show CBRK_SUPPLY_CHK 2>/dev/null | grep -o ': [0-9]*' | tr -dc 0-9)
  [ "$v" = 894281 ] && { echo "PASS battery: CBRK_SUPPLY_CHK=$v"; exit 0; }
  sleep 5
done
echo "FAIL battery: CBRK_SUPPLY_CHK=${v:-unset}, expected 894281"; exit 1
