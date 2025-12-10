# ROS2 Workspace

This workspace is mounted from your host machine, so all changes persist across container restarts.

## First Time Setup

Run this once to build the workspace:

```bash
cd ~/dexi_ws
./setup.sh
```

This will:
- Import dependencies from dexi.repos (if present)
- Build DEXI packages (px4_msgs is pre-built in the Docker image)
- Set up auto-sourcing

## Daily Usage

The workspace is automatically sourced when you open a new terminal.

### Adding Your Own Packages

```bash
cd ~/dexi_ws/src
# Create or clone your package here
ros2 pkg create --build-type ament_python my_package

# Build
cd ~/dexi_ws
colcon build

# Workspace is auto-sourced on next terminal
```

### Building

```bash
cd ~/dexi_ws
colcon build
```

### Testing PX4 Topics

After running setup, you can:

```bash
# List PX4 topics
ros2 topic list | grep fmu

# Echo vehicle status
ros2 topic echo /fmu/out/vehicle_status_v1

# Echo local position
ros2 topic echo /fmu/out/vehicle_local_position
```

## Workspace Structure

```
/opt/px4_ws/          # Pre-built in Docker image (read-only)
└── install/
    └── px4_msgs/     # PX4 message definitions (pre-compiled)

~/dexi_ws/            # Your workspace (mounted from host)
├── src/              # Source packages (your code goes here)
│   └── dexi_*/       # DEXI packages
├── build/            # Build artifacts (auto-generated)
├── install/          # Install space (auto-generated)
└── log/              # Build logs (auto-generated)
```

## Notes

- **px4_msgs** is pre-built in the Docker image at `/opt/px4_ws` - no need to build it yourself!
- The `build/`, `install/`, and `log/` directories are git-ignored
- Add your packages to `src/`
- Changes persist on your host machine at `./dexi_ws`
- Build times are much faster since px4_msgs is already compiled
