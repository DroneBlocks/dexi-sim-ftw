# Slim PX4 Gazebo-Classic SITL image — optical flow variant, built from
# upstream PX4 release/1.16 pinned to the commit that includes the flow-
# bootstrap fix (dakejahl's PR #26960, merged to main on 2026-04-02 and
# backported to release/1.16 as 75f9a32a12).
#
# Background: stock PX4 1.16 *before* that commit cannot start optical
# flow fusion when range is the height reference — a check deadlock in
# ekf2/aid_sources/optical_flow/optical_flow_control.cpp. We independently
# patched this in dbaldwin's fork in Feb 2026 but the identical upstream
# fix beat us to merge. We now pin to the upstream commit directly so
# there is no fork to maintain.
#
# To update the pin: find the tip of release/1.16 in PX4/PX4-Autopilot,
# replace PX4_COMMIT below, rebuild. To test a different branch (main,
# release/1.17, etc.), swap PX4_COMMIT and PX4_REF.

# ---- Builder: compile PX4 SITL + gazebo-classic iris_opt_flow target ----
# Using jonasvautherin/px4-gazebo-headless as the base because:
#   1. It already has every PX4 build dep installed (gcc, cmake, python,
#      colcon, ninja, gazebo-classic dev headers), so no apt-get needed.
#   2. It's published as a multi-arch image (amd64 + arm64), so on Apple
#      Silicon we compile native arm64 binaries rather than x86_64 ones
#      that would then need Rosetta emulation at runtime (the px4io/px4-dev-
#      simulation-focal image is amd64-only and breaks on Apple Silicon).
# We wipe its /root/Firmware and fetch a single pinned commit in its place.
FROM jonasvautherin/px4-gazebo-headless:1.16.0 AS builder

ENV DEBIAN_FRONTEND=noninteractive

# Pin to upstream release/1.16 @ 75f9a32a1269f2ac85381127182e18628c265981
# as of 2026-04-20 — first 1.16 commit with the optical flow bootstrap
# fix (dakejahl's PR #26960 backport). Matches what the real drone flies.
#
# We fetch by branch name and then `git checkout <sha>` because GitHub
# doesn't allow shallow-fetch of arbitrary commits (requires
# uploadpack.allowReachableSHA1InWant which is off by default). Depth 20
# is cheap and leaves room for the pin to lag a few upstream commits
# before we bump it.
ARG PX4_REPO=https://github.com/PX4/PX4-Autopilot.git
ARG PX4_REF=release/1.16
ARG PX4_COMMIT=75f9a32a1269f2ac85381127182e18628c265981

# The second fetch pulls v1.16.x tags explicitly. PX4's build runs
# `git describe --tags` to embed a version string; with a shallow clone
# that lacks the nearest tag, the Python script parsing the result errors
# with "No names found / IndexError: list index out of range" and the
# make fails.
#
# Same thing happens a second time for the NuttX submodule — PX4's
# version generator also reads the NuttX release tag (nuttx-X.Y.Z). A
# `--depth 1` submodule init doesn't fetch that tag. The third fetch,
# inside the NuttX submodule, pulls nuttx-* tags so the build proceeds.
RUN rm -rf /root/Firmware && \
    git init /root/Firmware && \
    cd /root/Firmware && \
    git remote add origin ${PX4_REPO} && \
    git fetch --depth 20 origin ${PX4_REF} && \
    git fetch --depth 20 origin 'refs/tags/v1.16*:refs/tags/v1.16*' && \
    git checkout ${PX4_COMMIT} && \
    git submodule update --init --recursive --depth 1 && \
    cd platforms/nuttx/NuttX/nuttx && \
    git fetch --depth 20 origin 'refs/tags/nuttx-*:refs/tags/nuttx-*'

WORKDIR /root/Firmware
# DONT_RUN=1 skips the post-build Gazebo launch; we just want artifacts.
# Build the iris_opt_flow target — compiles PX4 SITL, sitl_gazebo-classic,
# all plugins (including opticalflow + lidar), and libOpticalFlow.so.
RUN DONT_RUN=1 make px4_sitl_default gazebo-classic_iris_opt_flow

# ---- Runtime stage ----
FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:99

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
    libopencv-video4.2 \
    libopencv-calib3d4.2 \
    libopencv-features2d4.2 \
    libopencv-imgproc4.2 \
    libopencv-core4.2 \
    libopencv-flann4.2 \
    && apt-get purge -y wget lsb-release gnupg2 \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

ENV FIRMWARE_DIR=/opt/px4
ENV WORKSPACE_DIR=/opt/px4

# PX4 SITL binary and config built from our fork
COPY --from=builder /root/Firmware/build/px4_sitl_default/bin /opt/px4/bin
COPY --from=builder /root/Firmware/build/px4_sitl_default/etc /opt/px4/etc

# Gazebo plugins (.so files only)
COPY --from=builder /root/Firmware/build/px4_sitl_default/build_gazebo-classic/libgazebo_motor_model.so /opt/px4/gazebo-plugins/
COPY --from=builder /root/Firmware/build/px4_sitl_default/build_gazebo-classic/libgazebo_multirotor_base_plugin.so /opt/px4/gazebo-plugins/
COPY --from=builder /root/Firmware/build/px4_sitl_default/build_gazebo-classic/libgazebo_mavlink_interface.so /opt/px4/gazebo-plugins/
COPY --from=builder /root/Firmware/build/px4_sitl_default/build_gazebo-classic/libgazebo_imu_plugin.so /opt/px4/gazebo-plugins/
COPY --from=builder /root/Firmware/build/px4_sitl_default/build_gazebo-classic/libgazebo_magnetometer_plugin.so /opt/px4/gazebo-plugins/
COPY --from=builder /root/Firmware/build/px4_sitl_default/build_gazebo-classic/libgazebo_barometer_plugin.so /opt/px4/gazebo-plugins/
COPY --from=builder /root/Firmware/build/px4_sitl_default/build_gazebo-classic/libgazebo_gps_plugin.so /opt/px4/gazebo-plugins/
COPY --from=builder /root/Firmware/build/px4_sitl_default/build_gazebo-classic/libgazebo_groundtruth_plugin.so /opt/px4/gazebo-plugins/
COPY --from=builder /root/Firmware/build/px4_sitl_default/build_gazebo-classic/libgazebo_controller_interface.so /opt/px4/gazebo-plugins/
# Flow-specific plugins
COPY --from=builder /root/Firmware/build/px4_sitl_default/build_gazebo-classic/libgazebo_opticalflow_plugin.so /opt/px4/gazebo-plugins/
COPY --from=builder /root/Firmware/build/px4_sitl_default/build_gazebo-classic/libgazebo_lidar_plugin.so /opt/px4/gazebo-plugins/
# libOpticalFlow.so is the Klaus Lutz flow computation library — dlopen'd
# by the opticalflow plugin at runtime. Must be on LD_LIBRARY_PATH.
COPY --from=builder /root/Firmware/build/px4_sitl_default/build_gazebo-classic/OpticalFlow/libOpticalFlow.so /opt/px4/gazebo-plugins/

# Message type libs needed by plugins
COPY --from=builder /root/Firmware/build/px4_sitl_default/build_gazebo-classic/libstd_msgs.so /opt/px4/gazebo-plugins/
COPY --from=builder /root/Firmware/build/px4_sitl_default/build_gazebo-classic/libmav_msgs.so /opt/px4/gazebo-plugins/
COPY --from=builder /root/Firmware/build/px4_sitl_default/build_gazebo-classic/libsensor_msgs.so /opt/px4/gazebo-plugins/
COPY --from=builder /root/Firmware/build/px4_sitl_default/build_gazebo-classic/libnav_msgs.so /opt/px4/gazebo-plugins/
COPY --from=builder /root/Firmware/build/px4_sitl_default/build_gazebo-classic/libphysics_msgs.so /opt/px4/gazebo-plugins/

# Flow vehicle + sensor models
COPY --from=builder /root/Firmware/Tools/simulation/gazebo-classic/sitl_gazebo-classic/models/iris_opt_flow /opt/px4/models/iris_opt_flow
COPY --from=builder /root/Firmware/Tools/simulation/gazebo-classic/sitl_gazebo-classic/models/px4flow /opt/px4/models/px4flow
COPY --from=builder /root/Firmware/Tools/simulation/gazebo-classic/sitl_gazebo-classic/models/lidar /opt/px4/models/lidar
# Drop flow camera render rate from 100 Hz to 30 Hz. Without a GPU in
# the container Gazebo rasterizes every frame on CPU via OGRE, and this
# single rate is ~3x of gzserver's total CPU. The opticalflow plugin
# only publishes at outputRate=20 Hz, so 30 Hz leaves 50% headroom —
# no quality loss, just less wasted rendering.
RUN sed -i 's|<update_rate>100</update_rate>|<update_rate>30</update_rate>|' \
    /opt/px4/models/px4flow/px4flow.sdf
# iris_opt_flow.sdf <include>s the iris base model for meshes
COPY --from=builder /root/Firmware/Tools/simulation/gazebo-classic/sitl_gazebo-classic/models/iris /opt/px4/models/iris
# iris base model <include>s model://gps (sensor link, not GPS fusion);
# Gazebo won't load iris at all without it, which blocks the mavlink_interface
# plugin and leaves PX4 stuck waiting on TCP 4560.
COPY --from=builder /root/Firmware/Tools/simulation/gazebo-classic/sitl_gazebo-classic/models/gps /opt/px4/models/gps

# Worlds and world-referenced models
COPY --from=builder /root/Firmware/Tools/simulation/gazebo-classic/sitl_gazebo-classic/worlds/empty.world /opt/px4/worlds/empty.world
COPY --from=builder /root/Firmware/Tools/simulation/gazebo-classic/sitl_gazebo-classic/models/asphalt_plane /opt/px4/models/asphalt_plane

# MAVLink patching script (reused from base slim)
COPY edit_rcS.bash /opt/px4/edit_rcS.bash
RUN chmod +x /opt/px4/edit_rcS.bash

# Dexi indoor EKF parameter overrides applied on first boot
COPY rc.dexi /opt/px4/etc/init.d-posix/rc.dexi

COPY entrypoint.sh /opt/px4/entrypoint.sh
RUN chmod +x /opt/px4/entrypoint.sh

WORKDIR /opt/px4

ENTRYPOINT ["/opt/px4/entrypoint.sh"]
