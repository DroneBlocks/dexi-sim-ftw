FROM ros:jazzy

# Install essential tools and rosbridge
RUN apt-get update && apt-get install -y \
    ros-jazzy-rosbridge-server \
    python3-pip \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Install pysm (same as desktop)
RUN pip3 install --break-system-packages pysm

# Create workspace directory
RUN mkdir -p /home/ros/dexi_ws

# Set working directory
WORKDIR /home/ros

# Default command
CMD ["bash"]
