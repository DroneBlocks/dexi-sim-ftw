#!/bin/bash

echo "Stopping Rosbridge Server..."

if pgrep -f "rosbridge_websocket" > /dev/null; then
    pkill -f "rosbridge_websocket"
    sleep 1

    if ! pgrep -f "rosbridge_websocket" > /dev/null; then
        echo "✓ Rosbridge stopped successfully"
    else
        echo "✗ Failed to stop Rosbridge. Trying force kill..."
        pkill -9 -f "rosbridge_websocket"
    fi
else
    echo "Rosbridge is not running"
fi
