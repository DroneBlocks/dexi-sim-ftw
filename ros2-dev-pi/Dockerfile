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

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Default command - keeps container running
CMD ["tail", "-f", "/dev/null"]
