# Hetzner preview of the AprilTag sim stack

A cpx31 in Hetzner `hil` running the stack from this branch: the Jazzy headless ROS
image with code-server inside, the three.js environments in Unity's slot, the hold-ned
offboard manager, tag_nav, and the GCS with the AprilTag blocks. Built on the server from
shipped sources because GitHub refuses anonymous git fetches from Hetzner and the preview
images are not on Docker Hub yet. The production path (provisioner: pull and up) is unchanged.

## Where

| Service | URL |
|---|---|
| GCS | http://5.78.98.115/droneblocks |
| Simulator (DEXI Lab default, picker in the gear drawer) | http://5.78.98.115:1337/viewer-corridor.html?autoconnect=1 |
| Node-RED and the tag-navigation dashboard | http://5.78.98.115:1880 and http://5.78.98.115:1880/ui |
| code-server (password `droneblocks`, native rclpy) | http://5.78.98.115:9999 |
| rosbridge | ws://5.78.98.115:9090 |

Plain HTTP on the public address; the provisioner's Cloudflare tunnel is not in front of it.

## What runs

Eight containers: ros2-dev (Jazzy, rosbridge, code-server, tag_nav from the bringup),
micro-dds-agent (Jazzy), px4-sitl, mavlink-router, mavlink2rest, web-dashboard, node-red, sim-env.

Sources on the server: `/opt/dexi-sim` (this branch, with `dexi_ws/src` carrying the
dexi_offboard `feat/hold-ned`, dexi_apriltag `feat/tag-nav` and dexi_bringup
`feat/tag-nav-bringup` checkouts), `/opt/web-sim` (droneblocks-web-sim
`feat/apriltag-corridor-viewer`), `/opt/gcs` (dexi-droneblocks `feat/apriltag-nav-blocks`).
Build script and log: `/opt/deploy.sh`, `/opt/deploy.log`. Build times on 4 vCPU:
environment image 4 s, GCS 37 s, ROS image 11.5 min.

## Checked on the server

- bringup starts all nodes including tag_nav; rosbridge, code-server, GCS and Node-RED answer
- PX4 topics and the drone camera reach rosbridge clients; the GCS's embedded viewer connects
- arm, offboard takeoff to 1 m, land with auto-disarm
- the Node-RED flow engaged over tag 0 and flew the lab row to tag 5, landed and disarmed
- `apriltag_tag_hop.py` with rclpy from inside the ROS container: takeoff, centered on tag 0
  (8 cm), flew to tag 1, centered (6 cm), landed

## Found and fixed here

- An unpinned compose service took 172.20.0.2 before ros2-dev; sim-env is now pinned to .7.
- PX4's hover-thrust estimator converges to about 0.30 on this host after a few hops and
  Land mode then never reports landed. `MPC_USE_HTE=0` in the PX4 entrypoint fixes it.
- The stock simulated battery is flat after a minute armed. `SIM_BAT_DRAIN=7200`.
- The viewer defaulted its rosbridge address to localhost; it now defaults to the page host.
- The Node-RED flows directory is a submodule and must be present and owned by uid 1000.
- After importing the tag-navigation flow into a fresh Node-RED, restart the container once
  so its subscriptions register. The proper fix is shipping the flow tab in node-red-dexi.

## The camera

The drone camera is the simulator page. Whoever has the simulator open publishes it; with no
page open there is no camera and tag navigation reports the tag lost. A software-rendered
browser tab from a laptop lags several seconds; a normal tab with a GPU does not.

## Teardown

Delete the server from the Hetzner console or the API; the project label is
`purpose=sim-preview`. Nothing on it is needed afterwards; everything is in the branches.
