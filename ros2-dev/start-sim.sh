#!/bin/bash
# Container entry: fill the mounted workspace from the image if it is not built, start
# code-server, then run the sim bringup (which starts rosbridge) in the foreground.
set +u
WS=/home/ubuntu/dexi_ws

if [ ! -f $WS/install/setup.bash ] && [ -d /opt/dexi_ws_prebuilt/install ]; then
    echo "Populating workspace from the image..."
    cp -a /opt/dexi_ws_prebuilt/install /opt/dexi_ws_prebuilt/build $WS/
    cp -a /opt/dexi_ws_prebuilt/log $WS/ 2>/dev/null || true
    for pkg in /opt/dexi_ws_prebuilt/src/*/; do
        name=$(basename "$pkg")
        [ -d "$WS/src/$name" ] || cp -a "$pkg" "$WS/src/$name"
    done
fi

nohup code-server $WS > /tmp/code-server.log 2>&1 &

source /opt/ros/jazzy/setup.bash
if [ -f $WS/install/setup.bash ]; then
    source $WS/install/setup.bash
    exec ros2 launch dexi_bringup dexi_bringup_unity_sim.launch.py
fi
echo "Workspace not built; nothing to launch."
exec tail -f /dev/null
