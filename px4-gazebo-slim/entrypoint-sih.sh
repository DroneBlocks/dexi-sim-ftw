#!/bin/bash
# PX4 SITL on the built-in SIH simulator (simulator_sih): same binary, same
# airframe family as the Gazebo image, but no gzserver and no X server. The
# camera comes from the three.js court (corridor-sim), not from the physics.
set -e
IP_API="${1:-172.20.0.8}"
IP_QGC="${2:-172.20.0.8}"
echo "============================================"
echo "  PX4 SITL (SIH, no Gazebo)"
echo "  MAVLink API target: ${IP_API}:14540"
echo "  MAVLink GCS target: ${IP_QGC}:14550"
echo "  DDS: UDP port 8888"
echo "============================================"
mkdir -p /opt/px4/rootfs
cd /opt/px4/rootfs
export PATH="/opt/px4/bin:${PATH}"
export PX4_SYS_AUTOSTART=10040          # sihsim_quadx
export PX4_SIMULATOR=sihsim
export PX4_SIM_MODEL=quadx
CONFIG_FILE=/opt/px4/etc/init.d-posix/px4-rc.mavlink
sed -i "s/mavlink start -x -u \$udp_gcs_port_local -r 4000000/mavlink start -x -u \$udp_gcs_port_local -r 4000000 -t ${IP_QGC}/" ${CONFIG_FILE}
sed -i "s/mavlink start -x -u \$udp_offboard_port_local -r 4000000/mavlink start -x -u \$udp_offboard_port_local -r 4000000 -t ${IP_API}/" ${CONFIG_FILE}
exec px4 -d /opt/px4/etc -s /opt/px4/etc/init.d-posix/rcS
