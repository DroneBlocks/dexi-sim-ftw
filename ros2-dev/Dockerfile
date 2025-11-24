FROM tiryoh/ros2-desktop-vnc:humble

# Install dependencies
RUN sudo pip3 install pysm

RUN sudo apt update -y && \
    sudo apt install -y ros-humble-rosbridge-server && \
    sudo rm -rf /var/lib/apt/lists/*

# Copy startup script for rosbridge
COPY start-rosbridge.sh /usr/local/bin/start-rosbridge.sh
RUN chmod +x /usr/local/bin/start-rosbridge.sh
