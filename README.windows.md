# DEXI Simulation on Windows (WSL2)

This guide covers running the DEXI Simulation stack on Windows 10/11 using WSL2.

## Prerequisites

1.  **WSL2**: Ensure you are running WSL2 (not WSL1).
    ```powershell
    wsl --list --verbose
    # Should show version 2
    ```
2.  **Docker Desktop**: Enable "Use the WSL 2 based engine" in Docker Desktop settings.
3.  **X11 Server (Optional)**: For some GUI tools, though the VNC desktop (`localhost:6080`) is usually sufficient.

## Installation Steps

1.  **Clone inside WSL**:
    Always clone the repository into your WSL filesystem (e.g., `~/projects/dexi-sim-ftw`), NOT the Windows filesystem (`/mnt/c/...`). This improves performance and avoids file permission issues.

2.  **Permission Fixes**:
    Docker on Windows/WSL sometimes struggles with volume permissions. If you see permission errors with Node-RED, run:
    ```bash
    sudo chown -R 1000:1000 node-red-dexi/flows
    ```

## Accessing the VNC Desktop

The simulated development environment runs a full Ubuntu desktop accessible via browser.
- URL: http://localhost:6080
- No password required by default.

## Common Issues

### "File not found" or Volume Mounting Errors
Ensure you are running `docker compose up` from within the WSL terminal, not PowerShell.

### High Resource Usage
The simulation (Unity + Gazebo + ROS2) is heavy.
- Create a `.wslconfig` file in your Windows User directory (`C:\Users\YourUser\.wslconfig`) to limit memory if needed, or give it more if it crashes.
```ini
[wsl2]
memory=8GB
processors=4
```
