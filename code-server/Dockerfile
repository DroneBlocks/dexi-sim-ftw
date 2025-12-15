FROM codercom/code-server:latest

# Install Python and pip
RUN sudo apt-get update && \
    sudo apt-get install -y python3 python3-pip && \
    sudo rm -rf /var/lib/apt/lists/*

# Install MAVSDK
RUN pip3 install --break-system-packages mavsdk

# Set default workspace
WORKDIR /home/coder
