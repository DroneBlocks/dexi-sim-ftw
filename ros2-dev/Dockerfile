# Use the pre-built base image with px4_msgs
# Build and push the base with: docker build -f Dockerfile.base -t droneblocks/dexi-sim-ros2-base:humble-px4-1.16.0 .
FROM droneblocks/dexi-sim-ros2-base:humble-px4-1.16.0

# Copy startup scripts (these can be updated without rebuilding the base)
COPY start-rosbridge.sh /usr/local/bin/start-rosbridge.sh
COPY start-dexi-bringup.sh /usr/local/bin/start-dexi-bringup.sh
RUN chmod +x /usr/local/bin/start-rosbridge.sh && \
    chmod +x /usr/local/bin/start-dexi-bringup.sh
