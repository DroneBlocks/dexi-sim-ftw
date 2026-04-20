# px4-gazebo-slim-flow

PX4 Gazebo-Classic SITL image for the **indoor, GPS-less** Dexi config:
PAW3902 optical flow + range finder, no GPS, range as primary height
reference. Built from upstream PX4 release/1.16 at a pinned commit that
includes the optical-flow bootstrap fix (PR
[#26960](https://github.com/PX4/PX4-Autopilot/pull/26960)).

Sibling of `px4-gazebo-slim/` — that image stays untouched and keeps
serving the default GPS-equipped iris sim.

> **Status: R&D / dev-use, not the default cloud classroom image.**
> This image burns ~10× the CPU of the GPS slim image (see "Performance
> & scaling" below), so it's too heavy for classroom VMs. Use it for
> firmware validation, EKF debugging, fault-injection exercises, and
> any work that requires parity with the real indoor drone. Students on
> cloud deployments should keep running the default `px4-gazebo-slim`
> (GPS) image.

## Why a separate image

Two firmware-level things the stock slim image can't provide:

1. **Optical flow + lidar plugins in Gazebo.** The iris_opt_flow airframe,
   `px4flow`, and `lidar` sensor models with their runtime `.so` plugins.
2. **Our EKF patch.** `fix/optical-flow-range-height-bootstrap` on
   [`dbaldwin/PX4-Autopilot`](https://github.com/dbaldwin/PX4-Autopilot/tree/fix/optical-flow-range-height-bootstrap)
   breaks a check deadlock: stock PX4 refuses to start flow fusion when
   `EKF2_HGT_REF=2` (range) because terrain estimation is disabled and
   there's no horizontal aiding. The one-line fix recognizes that if range
   IS the height ref, ground plane is implicitly known. Without this patch,
   flow fusion never engages in sim (same as on the real drone before the
   patch).

## Build

```bash
# From repo root. First build is ~15 min (clones fork, compiles PX4 SITL).
docker compose -f docker-compose.yml -f docker-compose.flow.yml build px4-sitl
```

Subsequent builds are cached unless `Dockerfile`, `entrypoint.sh`, or
`rc.dexi` change.

## Run

```bash
# Flow-only stack — swaps the default px4-sitl image for the flow variant.
docker compose -f docker-compose.yml -f docker-compose.flow.yml up -d

# Back to the GPS stack — just drop the override.
docker compose up -d
```

Every other service (`ros2-dev`, `code-server`, `web-dashboard`, etc.)
talks to the same `px4-sitl` network endpoint, so DroneBlocks and the ROS2
offboard path work against this image unchanged.

**Recreating px4-sitl kills the DDS agent's netns.** If you `stop`/`up -d`
the px4-sitl container, also recreate `micro-dds-agent`:

```bash
docker compose -f docker-compose.yml -f docker-compose.flow.yml rm -sf micro-dds-agent
docker compose -f docker-compose.yml -f docker-compose.flow.yml up -d micro-dds-agent
```

Verify DDS is fully up with:

```bash
docker exec dexi-sim-ftw-ros2-dev-1 bash -c \
  "source /opt/ros/humble/setup.bash && ros2 topic list | grep -c ^/fmu/"
# Should print ~67. If it prints ~8, DDS is half-connected — recreate the agent.
```

## rc.dexi param overrides

Applied automatically on every PX4 boot. Mirrors the prod drone's config:

| Param | Value | Why |
|-------|-------|-----|
| `EKF2_HGT_REF` | 2 | Range sensor is primary height ref |
| `EKF2_RNG_CTRL` | 2 | Always fuse range |
| `EKF2_OF_QMIN` | 50 | Lower flow quality threshold |
| `SYS_HAS_GPS` | 0 | No GPS |
| `COM_ARM_WO_GPS` | 1 | Allow arming without GPS |
| `CBRK_SUPPLY_CHK` | 894281 | **Sim only** — no simulated battery monitor |

The airframe (`1010_gazebo-classic_iris_opt_flow`) already sets
`EKF2_GPS_CTRL=0`, `EKF2_OF_CTRL=1`, `LPE_FAKE_ORIGIN=1`, so those aren't
duplicated in `rc.dexi`.

## Smoke test — verify the wiring is alive

```bash
# After `up -d` and a ~25s settle, check all three sensor paths
docker exec dexi-sim-ftw-px4-sitl-1 sh -c \
  "gz topic -l | grep -E 'opticalFlow|laser/scan|groundtruth'"
# Expected: /gazebo/default/iris_opt_flow/{px4flow/link/opticalFlow,
#                                          lidar/link/laser/scan,
#                                          groundtruth}

# Confirm PX4 uORB is receiving the MAVLink-forwarded flow data
docker exec dexi-sim-ftw-px4-sitl-1 sh -c \
  "cd /opt/px4/rootfs && /opt/px4/bin/px4-listener sensor_optical_flow -n 1 \
   | head -15"
# Expected: device_id contains 'MAVLINK:0', non-zero timestamp

# Confirm range sensor → distance_sensor uORB → EKF height ref
docker exec dexi-sim-ftw-px4-sitl-1 sh -c \
  "cd /opt/px4/rootfs && /opt/px4/bin/px4-listener estimator_status_flags -n 1 \
   | grep -E 'cs_rng_hgt|cs_opt_flow|cs_tilt_align'"
# Expected on ground: cs_rng_hgt=True, cs_tilt_align=True, cs_opt_flow=False
# (flow only activates above SENS_FLOW_MINHGT=0.7m)
```

All of that verifies successfully in the current build — the EKF is in
the correct "flow armed but not yet fused" state that matches the real
drone on the ground.

## Validation script

`scripts/validate_flow_sim.py` (host-side) orchestrates:

- Three background `px4-listener` loops inside `px4-sitl` that write
  `vehicle_local_position`, `vehicle_local_position_groundtruth`, and
  `estimator_status_flags` to `/tmp/*.log` at 20 Hz for 60 s.
- A force-armed flight trigger run inside `ros2-dev` that publishes
  `OffboardNavCommand` to `/dexi/offboard_manager` and a raw
  `VehicleCommand` with `param2=21196` + `from_external=False` to
  `/fmu/in/vehicle_command`.
- After the flight, copies the three logs back to `./flight_logs/` and
  correlates EKF vs ground truth to print a PASS/FAIL summary.

```bash
python3 scripts/validate_flow_sim.py
# Or if you just want to re-parse logs from a previous run:
python3 scripts/validate_flow_sim.py --skip-flight
```

### Why simulated RC (not force-arm, not NAV_TAKEOFF)

Without RC, arming into OFFBOARD hits a chicken-and-egg: offboard mode
needs `local_position_valid`, which needs flow fusion, which needs
altitude > 0.7 m (`SENS_FLOW_MINHGT`). Force-arm bypasses *preflight*
but doesn't fix the mode-entry requirements, so the drone arms and
then immediately auto-disarms because it can't enter offboard. And
`VEHICLE_CMD_NAV_TAKEOFF` fails with "Switching to Takeoff is currently
not available" because AUTO_TAKEOFF wants a home position, which needs
global position we don't have.

The validation script publishes `ManualControlSetpoint` at 20 Hz as a
simulated MAVLink joystick source, sets mode to ALTCTL (which only needs
altitude from range), arms normally, ramps throttle to +0.9 for 7 s to
clear SENS_FLOW_MINHGT, and hovers for 10 s. This mirrors the real-drone
RC-in-POSCTL arming flow (throttle up manually, flow engages, position
estimate becomes valid).

One detail worth keeping: PX4 1.16's force-arm magic (`param2=21196`)
only skips preflight when `VehicleCommand.from_external=false`. External
commands with `from_external=true` always run preflight — see
`Commander.cpp:953`. Irrelevant to the current script but a trap if you
end up wanting a force-arm path later.

## Flight validation — currently passing

Running `python3 scripts/validate_flow_sim.py` completes a takeoff /
hover / land cycle and prints a summary like:

```
  flight peak altitude (truth)      : 4.418 m
  altitude hold mean (truth)        : 4.258 m
  altitude hold worst deviation     : 83.3 cm
  horizontal drift during hover     : 1.523 m
  EKF-vs-truth altitude err (peak)  : 7.4 cm
  EKF cs_opt_flow seen True         : True
  EKF cs_rng_hgt  seen True         : True

PASS: flow fusion engages airborne and EKF altitude tracks truth within tolerance
```

The two assertions that matter: `cs_opt_flow: True` means the
flow-bootstrap patch did its job (stock PX4 never flips this when range
is the height reference). `EKF altitude error: 7.4 cm` means range-fused
altitude tracks ground truth well.

Loose altitude hold (80+ cm) and horizontal drift (~1.5 m over 10 s) are
**expected and correct** for the test profile — we're driving the drone
with a simulated throttle stick in ALTCTL, not the offboard position
controller used in prod. Real drone altitude hold comes from
`dexi_offboard`'s 20 Hz position setpoints, not this control path. Flow-
only horizontal drift is a fundamental limit of velocity-only estimation
without a position reference.

## Files

```
px4-gazebo-slim-flow/
├── Dockerfile            # Multi-stage: compile upstream PX4 → slim arm64 runtime
├── entrypoint.sh         # Spawns iris_opt_flow, appends rc.dexi to rcS
├── rc.dexi               # EKF / arming param overrides
└── edit_rcS.bash         # Unchanged copy from base slim image

docker-compose.flow.yml              # Override that swaps px4-sitl → flow image
scripts/validate_flow_sim.py         # Passing flight, ~4m climb + hover + land
scripts/fault_test_range.py          # Disable range fusion mid-hover
scripts/fault_test_no_height.py      # Disable range + baro simultaneously
scripts/fault_test_flow.py           # Disable flow in POSCTL (visible drift)
```

## Performance & scaling

This is the reason this image is dev-only.

**Measured on a 14-core Apple Silicon Mac (Docker Desktop, arm64, no GPU):**

| | GPS slim (`iris`) | Flow slim (`iris_opt_flow`) | Delta |
|---|---|---|---|
| Idle CPU | ~30% | **~355%** | ~12× |
| Idle memory | 342 MiB | 287 MiB | comparable |
| Image size | 2.57 GB | 1.42 GB | comparable |
| Startup to first EKF sample | 7 s | 8 s | comparable |

### Where the CPU goes

`gzserver` accounts for ~465% of the ~500% total; `px4` itself only ~7%.
The cost is **software OGRE rendering for the opticalflow plugin's
camera sensor** — 64×64 grayscale frames rasterized by OpenCV on the
CPU because there's no GPU in the container. The lidar ray sensor also
contributes some, but the camera is the bulk.

The SDF is already patched in this image to render at 30 Hz (down from
upstream's 100 Hz) — the opticalflow plugin's `outputRate=20` Hz, so
30 Hz leaves 50% headroom with no quality loss. That saved ~23% CPU.

### What this means for cloud deployment

On a 3 vCPU Hetzner VM (or similar), one flow-sim instance consumes
~100% of available CPU. A GPS sim instance consumes ~10% of the same
VM and supports ~8 concurrent users. **The default classroom stack
should be the GPS sim.**

### Three paths forward if you need indoor sim at scale

1. **Ship GPS sim to students, keep flow sim for dev.** Zero work,
   clearest story. Lose: indoor scenarios, EKF-flow-specific exercises.
2. **Swap `libgazebo_opticalflow_plugin.so` for
   `libgazebo_opticalflow_mockup_plugin.so`.** Already in the builder
   image. Generates `HIL_OPTICAL_FLOW` from Gazebo ground-truth velocity
   + noise — no camera, no OGRE. Expected CPU: similar to GPS sim. PX4
   and EKF behavior is byte-for-byte identical because the uORB topic
   content is identical. Lose: realistic quality-degradation profiles
   (no low-texture / low-light failures). Fine for curriculum, wrong for
   validating flow firmware.
3. **Replace Gazebo with PX4 SIH + custom sensor bridge.** PX4's
   built-in Simulation-In-Hardware module runs physics inside PX4, no
   Gazebo at all. Write a small bridge to synthesize flow/lidar from
   PX4's state, feed back via HIL_SENSOR. Unity renders from
   `vehicle_odometry` as today. Expected CPU: 10–15%. Big engineering
   lift (1–2 weeks) but genuinely scalable.

Option 1 is where we are. Options 2 and 3 are documented here so
future-us has the menu when it's time to revisit.


## Build-time gotchas (captured for future-you)

All resolved in the current Dockerfile, but worth knowing in case
something regresses:

- `iris_opt_flow.sdf` `<include>`s the `iris` base model, which
  `<include>`s `model://gps` (a sensor link, not GPS fusion). Without the
  `gps` model copied in, iris fails to load and the mavlink_interface
  plugin never binds, so PX4 hangs on `TCP 4560 waiting for simulator`.
- Spawn must be `--model-name=iris_opt_flow` (matching the SDF root
  name). Spawning as `--model-name=iris` silently produces valid Gazebo
  topics but the nested mavlink_interface plugin subscribes to the wrong
  path and flow never reaches PX4 uORB.
- The opticalflow plugin uses a camera sensor → needs OGRE shaders from
  `/usr/share/gazebo-11`. Source `/usr/share/gazebo-11/setup.sh` before
  setting our custom `GAZEBO_RESOURCE_PATH` so the default paths aren't
  clobbered; otherwise `CameraSensor` creation fails and the plugin
  doesn't publish anything.
- `libgazebo_opticalflow_plugin.so` dlopens `libOpticalFlow.so` (the
  Klaus Lutz flow library) and links against 4.2-era OpenCV. Both must be
  present in the runtime layer.
- `px4-listener` with `-n > 1` hangs without printing output in this PX4
  build. The validation script works around it by looping `-n 1` at the
  target rate — fine for 20 Hz logging.
- Builder base is `jonasvautherin/px4-gazebo-headless:1.16.0` (multi-
  arch), **not** `px4io/px4-dev-simulation-focal` (amd64-only). The
  latter compiles x86_64 binaries that fail under Rosetta on Apple
  Silicon.
- **Stale Xvfb locks on restart kill flow silently.** If `/tmp/.X99-lock`
  or `/tmp/.X11-unix/X99` carry over from a previous container, Xvfb
  refuses to start and Gazebo falls back to "Rendering disabled". The
  opticalflow plugin needs a camera sensor and camera sensors need
  rendering, so flow stops publishing with only a single easy-to-miss
  warning in the log. The entrypoint now `rm -f`s both paths before
  starting Xvfb and polls for the socket to appear.
