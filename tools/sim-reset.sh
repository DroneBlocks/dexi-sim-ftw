#!/usr/bin/env bash
# Put the SITL aircraft back on tag 0 without restarting anything.
#
# Moves the Gazebo model to the origin (facing east, as it spawns) and waits for
# PX4's estimator to follow, which takes about 12 s. The aircraft must be
# disarmed. No container restarts, no estimator reset, nodes keep running.
#
#   tools/sim-reset.sh              # tag 0
#   tools/sim-reset.sh 0 3.0        # north, east in meters (tag 2 on the court)
set -euo pipefail
NORTH="${1:-0}"; EAST="${2:-0}"
PX4=${PX4_CONTAINER:-dexi-sim-ftw-px4-sitl-1}
px4() { docker exec "$PX4" sh -c "export PATH=/opt/px4/bin:\$PATH; cd /opt/px4/rootfs; $*"; }
if px4 "px4-commander status" 2>/dev/null | grep -q "Armed"; then
  echo "aircraft is armed; land and disarm first" >&2; exit 1
fi
# Gazebo is ENU: x east, y north. PX4 reports NED.
px4 "gz model -m iris -x $EAST -y $NORTH -z 0.12 -R 0 -P 0 -Y 1.5708"
printf "moved; waiting for the estimator "
for _ in $(seq 1 25); do
  sleep 1; printf "."
  read -r x y < <(px4 "px4-listener vehicle_local_position -n 1" 2>/dev/null | awk '/^ *x:/{x=$2} /^ *y:/{y=$2} END{print x, y}')
  if awk -v x="$x" -v y="$y" -v n="$NORTH" -v e="$EAST" 'BEGIN{exit !((x-n)^2+(y-e)^2 < 0.15^2)}'; then
    echo; echo "estimator at N $x E $y (target N $NORTH E $EAST)"; exit 0
  fi
done
echo; echo "estimator did not settle: N ${x:-?} E ${y:-?}" >&2; exit 2
