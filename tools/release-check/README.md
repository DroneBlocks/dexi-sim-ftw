# Release check

Functional checks against a running sim stack, the way students use it: Blockly demo missions
through the GCS page, the Node-RED tag-navigation flow, the rclpy tag-hop example from inside the
ROS container, a MAVSDK mission over mavlink-router, and two regressions. Twelve to fifteen minutes.

```bash
# local stack
tools/release-check/check.sh
# a deployed stack (docker commands over ssh, pages over http)
HOST=203.0.113.5 DOCKER_HOST=ssh://root@203.0.113.5 tools/release-check/check.sh
# a subset
tools/release-check/check.sh stack nodered-flow
```

Needs Node 18+ on the machine running it (Playwright is installed on first run), Docker access to
the stack's daemon, and the GCS repo checkout for the demo missions (`DEMOS=.../assets/ts/demos.ts`).
Every flight check restarts PX4 first so the aircraft starts at the origin over tag 0 with a full
battery. The viewer page a check opens is also the drone camera. Logs land in `tools/release-check/logs/`.

## Checks

| Check | What it proves |
|---|---|
| `stack` | every service answers; PX4 topics, the camera, the detector, tag_nav and the manager reach rosbridge clients |
| `blockly-takeoff-land`, `blockly-square` | demo missions flown through the real GCS page, judged by the GCS's own verdict and a disarmed aircraft |
| `nodered-flow` | the tag-navigation flow runs its route and lands within 0.5 m of the last tag |
| `python-offboard` | `apriltag_tag_hop.py` with rclpy inside the ROS container, tag 0 to tag 1 |
| `color` | the color detection node reports each of the five DEXI Lab color pads from 1 m |
| `yolo` | dexi_yolo (AVR 2026 model, 1 Hz) detects eight lab stickers from 0.6 m; bridges 2 and 3 are excluded until line counting is solved |
| `mavsdk` | `takeoff_and_land.py` from dexi-mavsdk, inside the ROS container, over mavlink-router's 14540 feed |
| `regressions` | arm then disarm on the ground; a new takeoff after a hold_ned mission |

`logs/summary.txt` has the last run's table; `logs/<check>.log` the detail. The command exits
nonzero if anything failed, so it can gate a release.
