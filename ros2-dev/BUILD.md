# Building and Publishing the ROS2 Base Image

This directory now uses a two-layer Docker image strategy to speed up builds:

1. **Base Image** (`droneblocks/dexi-sim-ros2-base`) - Contains ROS2 Humble + pre-built px4_msgs
2. **Dev Image** (`ros2-dev`) - Adds startup scripts and mounts your workspace

## Quick Start (For Developers)

If you're just using the existing images, nothing changes! Just run:

```bash
docker-compose up
```

The base image will be pulled from Docker Hub automatically.

## Building the Base Image (Maintainers Only)

The base image only needs to be rebuilt when:
- Updating to a new PX4 version
- Updating ROS2 dependencies
- Updating the base ROS2 version

### Step 1: Build the Base Image

```bash
cd ros2-dev
docker build -f Dockerfile.base -t droneblocks/dexi-sim-ros2-base:humble-px4-1.16.0 .
```

Build time: ~10-15 minutes (one-time cost)

### Step 2: Test the Base Image Locally

Update `Dockerfile.new` if needed, then test locally:

```bash
docker build -f Dockerfile.new -t ros2-dev-test .
```

### Step 3: Push to Docker Hub

```bash
# Login to Docker Hub
docker login

# Push the base image
docker push droneblocks/dexi-sim-ros2-base:humble-px4-1.16.0
```

### Step 4: Switch to the New Dockerfile

Once the base image is pushed and tested:

```bash
# Backup old Dockerfile
mv Dockerfile Dockerfile.old

# Use the new one
mv Dockerfile.new Dockerfile
```

## Image Versioning

Base images are tagged with:
- `humble-px4-X.Y.Z` - Specific PX4 version (e.g., `humble-px4-1.16.0`)

Example tags:
- `droneblocks/dexi-sim-ros2-base:humble-px4-1.16.0`
- `droneblocks/dexi-sim-ros2-base:humble-px4-1.15.0`

## What's in Each Layer?

### Base Image (`Dockerfile.base`)
- Ubuntu + ROS2 Humble Desktop + VNC
- Pre-built px4_msgs (from PX4 GitHub)
- ROS2 dependencies (rosbridge, cv_bridge, etc.)
- Python dependencies (pysm)
- Located at: `/opt/px4_ws/install/`

### Dev Image (`Dockerfile` / `Dockerfile.new`)
- Based on the base image above
- Adds startup scripts (can be updated without rebuilding base)
- Mounts your workspace at runtime

## Benefits

- **Faster builds**: px4_msgs is pre-compiled (saves 5-10 minutes)
- **Faster iteration**: Only rebuild dev image when scripts change
- **Consistency**: Everyone uses the same px4_msgs version
- **Disk space**: Docker caches the base layer across all developers

## Troubleshooting

### Base image not found
If you get "image not found" errors:
```bash
# Pull the base image manually
docker pull droneblocks/dexi-sim-ros2-base:humble-px4-1.16.0
```

### px4_msgs version mismatch
Check your PX4 SITL version in `docker-compose.yml`:
```yaml
px4-sitl:
  image: jonasvautherin/px4-gazebo-headless:1.16.0  # Match this version
```

The base image should match: `droneblocks/dexi-sim-ros2-base:humble-px4-1.16.0`

### Need a different PX4 version?
Build a new base image with the appropriate branch:
```dockerfile
# In Dockerfile.base, change this line:
RUN git clone https://github.com/PX4/px4_msgs.git --branch release/1.15 --single-branch
```

Then tag appropriately: `droneblocks/dexi-sim-ros2-base:humble-px4-1.15.0`
