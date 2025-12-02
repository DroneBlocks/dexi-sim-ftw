FROM tiryoh/ros2-desktop-vnc:humble

# Install dependencies
RUN sudo pip3 install pysm

RUN sudo apt update -y && \
    sudo apt install -y \
        ros-humble-rosbridge-server \
        ros-humble-image-transport-plugins \
        ros-humble-cv-bridge \
        ros-humble-camera-info-manager && \
    sudo rm -rf /var/lib/apt/lists/*

# Copy startup scripts
COPY start-rosbridge.sh /usr/local/bin/start-rosbridge.sh
COPY start-dexi-bringup.sh /usr/local/bin/start-dexi-bringup.sh
RUN chmod +x /usr/local/bin/start-rosbridge.sh && \
    chmod +x /usr/local/bin/start-dexi-bringup.sh
