# Slim PX4 Gazebo-Classic SITL image
# Uses the existing jonasvautherin image as builder (already compiled),
# copies only runtime artifacts to a fresh image with gazebo11 runtime only.
# Result: ~1.5-2GB instead of 11GB, identical physics fidelity.

# ---- Builder: extract artifacts from the pre-built image ----
FROM jonasvautherin/px4-gazebo-headless:1.16.0 AS builder

# Nothing to build — everything is already compiled.
# We just need to identify and stage the runtime files.

# ---- Runtime stage ----
FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:99

# Install only Gazebo 11 runtime (not -dev) and minimal dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    wget \
    lsb-release \
    gnupg2 \
    && wget https://packages.osrfoundation.org/gazebo.gpg -O /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/gazebo-stable.list > /dev/null \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
    gazebo11 \
    libgazebo11 \
    xvfb \
    iproute2 \
    && apt-get purge -y wget lsb-release gnupg2 \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

ENV FIRMWARE_DIR=/opt/px4
ENV WORKSPACE_DIR=/opt/px4

# Copy PX4 SITL binary and config
COPY --from=builder /root/Firmware/build/px4_sitl_default/bin /opt/px4/bin
COPY --from=builder /root/Firmware/build/px4_sitl_default/etc /opt/px4/etc

# Copy Gazebo plugins (.so files only, not build artifacts)
COPY --from=builder /root/Firmware/build/px4_sitl_default/build_gazebo-classic/libgazebo_motor_model.so /opt/px4/gazebo-plugins/
COPY --from=builder /root/Firmware/build/px4_sitl_default/build_gazebo-classic/libgazebo_multirotor_base_plugin.so /opt/px4/gazebo-plugins/
COPY --from=builder /root/Firmware/build/px4_sitl_default/build_gazebo-classic/libgazebo_mavlink_interface.so /opt/px4/gazebo-plugins/
COPY --from=builder /root/Firmware/build/px4_sitl_default/build_gazebo-classic/libgazebo_imu_plugin.so /opt/px4/gazebo-plugins/
COPY --from=builder /root/Firmware/build/px4_sitl_default/build_gazebo-classic/libgazebo_magnetometer_plugin.so /opt/px4/gazebo-plugins/
COPY --from=builder /root/Firmware/build/px4_sitl_default/build_gazebo-classic/libgazebo_barometer_plugin.so /opt/px4/gazebo-plugins/
COPY --from=builder /root/Firmware/build/px4_sitl_default/build_gazebo-classic/libgazebo_gps_plugin.so /opt/px4/gazebo-plugins/
COPY --from=builder /root/Firmware/build/px4_sitl_default/build_gazebo-classic/libgazebo_groundtruth_plugin.so /opt/px4/gazebo-plugins/
COPY --from=builder /root/Firmware/build/px4_sitl_default/build_gazebo-classic/libgazebo_controller_interface.so /opt/px4/gazebo-plugins/
# Message type libs needed by plugins
COPY --from=builder /root/Firmware/build/px4_sitl_default/build_gazebo-classic/libstd_msgs.so /opt/px4/gazebo-plugins/
COPY --from=builder /root/Firmware/build/px4_sitl_default/build_gazebo-classic/libmav_msgs.so /opt/px4/gazebo-plugins/
COPY --from=builder /root/Firmware/build/px4_sitl_default/build_gazebo-classic/libsensor_msgs.so /opt/px4/gazebo-plugins/
COPY --from=builder /root/Firmware/build/px4_sitl_default/build_gazebo-classic/libnav_msgs.so /opt/px4/gazebo-plugins/
COPY --from=builder /root/Firmware/build/px4_sitl_default/build_gazebo-classic/libphysics_msgs.so /opt/px4/gazebo-plugins/

# Copy iris model and worlds
COPY --from=builder /root/Firmware/Tools/simulation/gazebo-classic/sitl_gazebo-classic/models/iris /opt/px4/models/iris
COPY --from=builder /root/Firmware/Tools/simulation/gazebo-classic/sitl_gazebo-classic/worlds/empty.world /opt/px4/worlds/empty.world
# Copy sensor models referenced by iris
COPY --from=builder /root/Firmware/Tools/simulation/gazebo-classic/sitl_gazebo-classic/models/gps /opt/px4/models/gps
# Copy world-referenced models (sun/ground_plane come with gazebo11 runtime)
COPY --from=builder /root/Firmware/Tools/simulation/gazebo-classic/sitl_gazebo-classic/models/asphalt_plane /opt/px4/models/asphalt_plane

# Copy MAVLink patching script
COPY edit_rcS.bash /opt/px4/edit_rcS.bash
RUN chmod +x /opt/px4/edit_rcS.bash

# Copy entrypoint
COPY entrypoint.sh /opt/px4/entrypoint.sh
RUN chmod +x /opt/px4/entrypoint.sh

WORKDIR /opt/px4

ENTRYPOINT ["/opt/px4/entrypoint.sh"]
