# Use pre-built multi-arch base image (includes px4_msgs and ROS2 dependencies)
FROM droneblocks/dexi-sim-ros2-base:humble-px4-1.16.0

WORKDIR /home/ubuntu

# Copy startup scripts (these can be updated without rebuilding the base)
COPY start-rosbridge.sh /usr/local/bin/start-rosbridge.sh
COPY start-dexi-bringup.sh /usr/local/bin/start-dexi-bringup.sh
RUN chmod +x /usr/local/bin/start-rosbridge.sh && \
    chmod +x /usr/local/bin/start-dexi-bringup.sh

# Auto-source dexi_ws if it exists (volume-mounted at runtime)
RUN echo '[ -f ~/dexi_ws/install/setup.bash ] && source ~/dexi_ws/install/setup.bash' >> /home/ubuntu/.bashrc

# Healthcheck: Wait for Rosbridge (9090) to be ready
HEALTHCHECK --interval=5s --timeout=3s --start-period=30s --retries=5 \
  CMD python3 -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.connect(('localhost', 9090))" || exit 1
