#!/bin/bash
set -e

# DEXI Simulation Quickstart Script
# Support: https://github.com/DroneBlocks/dexi-sim-ftw

echo "🚀 Starting DEXI Simulation Quickstart..."

# 1. Check for Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker Desktop first."
    exit 1
fi

echo "✅ Docker detected."

# 2. Fix Permissions (common issue with Node-RED on Linux/WSL)
if [[ "$OSTYPE" == "linux-gnu"* ]] || [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🔧 Setting permissions for Node-RED..."
    # Create directory if it doesn't exist to avoid errors
    mkdir -p node-red-dexi/flows
    # Use sudo to ensure we can change ownership
    sudo chown -R 1000:1000 node-red-dexi/flows
    echo "✅ Permissions set."
fi

# 3. Start Services
echo "🐳 Starting containers with Docker Compose..."
docker compose up -d

# 4. Show Status
echo ""
echo "🎉 Simulation is running!"
echo "---------------------------------------------------"
echo "🌍 Unity City:      http://localhost:1337"
echo "🕹️  Ground Control:  http://localhost"
echo "🧠 Node-RED:        http://localhost:1880"
echo "💻 VNC Desktop:     http://localhost:6080"
echo "---------------------------------------------------"
echo "To stop: docker compose down"
