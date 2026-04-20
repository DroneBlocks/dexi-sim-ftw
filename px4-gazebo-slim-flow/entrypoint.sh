#!/bin/bash
set -e

# PX4 Gazebo-Classic SITL (slim) — optical flow variant.
# Drop-in-compatible with the GPS slim image: same MAVLink endpoints,
# same code-server / ROS2 / DroneBlocks plumbing. Only the sim model and
# EKF params change.
# Usage: entrypoint.sh [IP_API] [IP_QGC]

IP_API="${1:-172.20.0.8}"
IP_QGC="${2:-172.20.0.8}"

echo "============================================"
echo "  PX4 Gazebo-Classic SITL (slim, flow)"
echo "  Model: iris_opt_flow (no GPS, range + flow)"
echo "  MAVLink API target: ${IP_API}:14540"
echo "  MAVLink GCS target: ${IP_QGC}:14550"
echo "  DDS: UDP port 8888"
echo "============================================"

mkdir -p /opt/px4/rootfs
cd /opt/px4/rootfs

export PATH="/opt/px4/bin:${PATH}"
# Source Gazebo's defaults so GAZEBO_RESOURCE_PATH / GAZEBO_PLUGIN_PATH include
# /usr/share/gazebo-11 and /usr/lib/*/gazebo-11/plugins. The opticalflow
# plugin uses a CameraSensor which needs OGRE's rtshaderlib from the stock
# gazebo-11 media tree — without these, scene init fails and flow never runs.
. /usr/share/gazebo-11/setup.sh
export GAZEBO_PLUGIN_PATH="/opt/px4/gazebo-plugins:${GAZEBO_PLUGIN_PATH}"
export LD_LIBRARY_PATH="/opt/px4/gazebo-plugins:${LD_LIBRARY_PATH}"
export GAZEBO_MODEL_PATH="/opt/px4/models:${GAZEBO_MODEL_PATH}"
export GAZEBO_RESOURCE_PATH="/opt/px4/worlds:${GAZEBO_RESOURCE_PATH}"

# iris_opt_flow airframe (1010_gazebo-classic_iris_opt_flow)
export PX4_SYS_AUTOSTART=1010
export PX4_SIM_MODEL=iris_opt_flow
export PX4_SIMULATOR=gazebo

# Patch MAVLink config to forward to API/GCS targets
CONFIG_FILE=/opt/px4/etc/init.d-posix/px4-rc.mavlink
sed -i "s/mavlink start -x -u \$udp_gcs_port_local -r 4000000/mavlink start -x -u \$udp_gcs_port_local -r 4000000 -t ${IP_QGC}/" ${CONFIG_FILE}
sed -i "s/mavlink start -x -u \$udp_offboard_port_local -r 4000000/mavlink start -x -u \$udp_offboard_port_local -r 4000000 -t ${IP_API}/" ${CONFIG_FILE}

# Inject Dexi indoor EKF param overrides on first boot. PX4's rcS sources
# files in init.d-posix; appending a chain line runs rc.dexi after the
# airframe defaults have been applied so our overrides win.
RCS_FILE=/opt/px4/etc/init.d-posix/rcS
if ! grep -q 'rc.dexi' "${RCS_FILE}"; then
    echo '. /opt/px4/etc/init.d-posix/rc.dexi' >> "${RCS_FILE}"
fi

# Clean stale X state from a prior container exit — if the /tmp/.X99-lock
# and /tmp/.X11-unix/X99 socket are still present, Xvfb refuses to start
# and Gazebo falls back to "Rendering disabled", which silently kills the
# opticalflow plugin's camera sensor. The whole optical-flow pipeline dies
# at that point with no obvious user-visible error beyond a single warning
# early in the log.
rm -f /tmp/.X99-lock /tmp/.X11-unix/X99
Xvfb :99 -screen 0 1600x1200x24+32 &
# Wait for Xvfb to actually bind the socket, not just the background & to
# return. 1s is usually enough but can race on cold container start.
for i in 1 2 3 4 5; do
    [ -S /tmp/.X11-unix/X99 ] && break
    sleep 1
done
if [ ! -S /tmp/.X11-unix/X99 ]; then
    echo "WARN: Xvfb did not come up in time; rendering will be disabled"
fi

gzserver --verbose /opt/px4/worlds/empty.world &
GAZEBO_PID=$!
sleep 3

# model-name must match the SDF's <model name='iris_opt_flow'> — otherwise
# the mavlink_interface plugin (inside the nested iris base) subscribes to
# the wrong gz topic path and optical flow never reaches PX4 uORB.
gz model --spawn-file=/opt/px4/models/iris_opt_flow/iris_opt_flow.sdf --model-name=iris_opt_flow -x 1.01 -y 0.98 -z 0.83
echo "iris_opt_flow model spawned into Gazebo"

exec px4 -d /opt/px4/etc -s /opt/px4/etc/init.d-posix/rcS
