FROM coder/code-server:4.108.2

# Install Python and pip
RUN sudo apt-get update && \
    sudo apt-get install -y python3 python3-pip && \
    sudo rm -rf /var/lib/apt/lists/*

# Install MAVSDK
RUN pip3 install --break-system-packages mavsdk

# Install Python extension for run button support
RUN code-server --install-extension ms-python.python

# Set default workspace
WORKDIR /home/coder
