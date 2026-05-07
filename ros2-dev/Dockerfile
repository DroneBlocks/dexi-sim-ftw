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

# Strip browsers from the VNC desktop. Cloud-sim students access the dashboard
# from their host browser (port 6080 noVNC, port 80 web-dashboard); they have
# no need to browse the open web from inside the container.
RUN sudo apt-get update && \
    sudo apt-get purge -y firefox firefox-esr chromium chromium-browser epiphany-browser konqueror midori 2>/dev/null || true && \
    sudo apt-get autoremove -y && \
    sudo rm -rf /var/lib/apt/lists/* \
                /usr/share/applications/firefox*.desktop \
                /usr/share/applications/chromium*.desktop \
                /home/ubuntu/Desktop/firefox*.desktop \
                /home/ubuntu/Desktop/chromium*.desktop
