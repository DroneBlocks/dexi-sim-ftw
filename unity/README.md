# DEXI City

Unity WebGL sim served via Docker.

## Building Multi-Architecture Images

To support both ARM64 (Mac, Raspberry Pi) and AMD64 (Intel/AMD servers), build and push multi-architecture images:

### One-Time Setup

Create a buildx builder (only needed once):
```bash
docker buildx create --name multiarch --driver docker-container --use
docker buildx inspect --bootstrap
```

### Build and Push Multi-Arch Image

Build for both ARM64 and AMD64 platforms and push to Docker Hub:
```bash
docker buildx build --platform linux/amd64,linux/arm64 \
  --no-cache \
  -t droneblocks/dexi-sitl-city:latest \
  --push \
  .
```

**Note**: Multi-platform builds require `--push` to push directly to a registry (Docker Hub). Make sure you're logged in first:
```bash
docker login
```

### Single Platform Build (Local Development)

For local testing on your current platform only:
```bash
docker build --no-cache -t droneblocks/dexi-sitl-city:latest .
```

## Running with Docker

Run the container (in background, auto-restart on reboot):
```bash
docker run -d --restart=unless-stopped -p 1337:1337 --name dexi-city droneblocks/dexi-sitl-city:latest
```

Access the sim at `http://localhost:1337`

Stop the container:
```bash
docker stop dexi-city
```

Remove the container:
```bash
docker rm dexi-city
```
