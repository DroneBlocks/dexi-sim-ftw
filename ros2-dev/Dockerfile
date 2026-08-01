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

# See Dockerfile.sim for the rationale: `docker compose exec` logs you in as
# root with HOME=/root, but the workspace bind mount is at /home/ubuntu/dexi_ws.
RUN ln -sfn /home/ubuntu/dexi_ws /root/dexi_ws && \
    ln -sfn /home/ubuntu/scripts /root/scripts && \
    ln -sfn /home/ubuntu/dexi-mavsdk /root/dexi-mavsdk && \
    echo 'source /opt/ros/humble/setup.bash' >> /root/.bashrc && \
    echo '[ -f /opt/px4_ws/install/setup.bash ] && source /opt/px4_ws/install/setup.bash' >> /root/.bashrc && \
    echo '[ -f /home/ubuntu/dexi_ws/install/setup.bash ] && source /home/ubuntu/dexi_ws/install/setup.bash' >> /root/.bashrc

# Strip browsers from the VNC desktop. See Dockerfile.sim for the production
# equivalent and rationale (tiryoh ships Firefox via /opt tarball, not apt).
RUN sudo bash -c 'set -e; \
    apt-get update; \
    pkgs=$(dpkg-query -W -f="\${Package}\n" "firefox*" "chromium*" "epiphany*" "midori*" "konqueror*" 2>/dev/null | tr "\n" " "); \
    if [ -n "$pkgs" ]; then apt-get purge -y $pkgs; fi; \
    apt-get autoremove -y; \
    rm -rf /usr/bin/firefox* /usr/bin/chromium* \
           /usr/lib/firefox* /usr/lib/chromium* \
           /opt/firefox* /opt/chromium* \
           /snap/firefox /snap/chromium; \
    find /usr/share/applications /etc/skel/Desktop /home/ubuntu/Desktop /home/ubuntu/.local/share/applications \
         \( -iname "firefox*.desktop" -o -iname "chromium*.desktop" \) \
         -delete 2>/dev/null || true; \
    rm -rf /var/lib/apt/lists/*'
