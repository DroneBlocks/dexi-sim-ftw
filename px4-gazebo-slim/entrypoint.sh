#!/bin/bash
set -e

# PX4 Gazebo-Classic Slim SITL entrypoint
# Drop-in replacement for jonasvautherin/px4-gazebo-headless
# Usage: entrypoint.sh [IP_API] [IP_QGC]

IP_API="${1:-172.20.0.8}"
IP_QGC="${2:-172.20.0.8}"

echo "============================================"
echo "  PX4 Gazebo-Classic SITL (slim)"
echo "  MAVLink API target: ${IP_API}:14540"
echo "  MAVLink GCS target: ${IP_QGC}:14550"
echo "  DDS: UDP port 8888"
echo "============================================"

# PX4 needs a writable working directory
mkdir -p /opt/px4/rootfs
cd /opt/px4/rootfs

# Add PX4 bin to PATH
export PATH="/opt/px4/bin:${PATH}"

# Set Gazebo environment
export GAZEBO_PLUGIN_PATH="/opt/px4/gazebo-plugins:${GAZEBO_PLUGIN_PATH}"
export LD_LIBRARY_PATH="/opt/px4/gazebo-plugins:${LD_LIBRARY_PATH}"
export GAZEBO_MODEL_PATH="/opt/px4/models:/usr/share/gazebo-11/models:${GAZEBO_MODEL_PATH}"
export GAZEBO_RESOURCE_PATH="/opt/px4/worlds:${GAZEBO_RESOURCE_PATH}"

# Select iris airframe with Gazebo
export PX4_SYS_AUTOSTART=10016
export PX4_SIM_MODEL=iris
export PX4_SIMULATOR=gazebo

# Patch MAVLink config to send to target IPs
CONFIG_FILE=/opt/px4/etc/init.d-posix/px4-rc.mavlink
sed -i "s/mavlink start -x -u \$udp_gcs_port_local -r 4000000/mavlink start -x -u \$udp_gcs_port_local -r 4000000 -t ${IP_QGC}/" ${CONFIG_FILE}
sed -i "s/mavlink start -x -u \$udp_offboard_port_local -r 4000000/mavlink start -x -u \$udp_offboard_port_local -r 4000000 -t ${IP_API}/" ${CONFIG_FILE}

# Start Xvfb for headless Gazebo
Xvfb :99 -screen 0 1600x1200x24+32 &
sleep 1

# Start Gazebo server (headless, no GUI)
gzserver --verbose /opt/px4/worlds/empty.world &
GAZEBO_PID=$!
sleep 3

# Spawn the iris model into Gazebo
# (The original image does this via make target; we do it directly)
gz model --spawn-file=/opt/px4/models/iris/iris.sdf --model-name=iris -x 0 -y 0 -z 0
echo "Iris model spawned into Gazebo"

# Start PX4 SITL
# PX4's simulator_mavlink module connects to Gazebo's MAVLink plugin on TCP 4560
exec px4 -d /opt/px4/etc -s /opt/px4/etc/init.d-posix/rcS
