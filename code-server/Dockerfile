FROM codercom/code-server:latest

# Install Python and pip
RUN sudo apt-get update && \
    sudo apt-get install -y python3 python3-pip && \
    sudo rm -rf /var/lib/apt/lists/*

# Install MAVSDK
RUN pip3 install --break-system-packages mavsdk

# Install Python extension for run button support
RUN code-server --install-extension ms-python.python

# Built-in AI/Chat off so the editor opens without the "Build with Agent" sidebar.
RUN mkdir -p /home/coder/.local/share/code-server/User && \
    printf '{\n  "chat.disableAIFeatures": true,\n  "workbench.secondarySideBar.defaultVisibility": "hidden"\n}\n' > /home/coder/.local/share/code-server/User/settings.json

# Set default workspace
WORKDIR /home/coder
