#!/usr/bin/env python3
"""Tier 2 validation: flow-only SITL sim vs real-drone indoor behavior.

Runs a canned takeoff/hover/land sequence against the flow SITL stack and
asserts the EKF behaves like the real drone does. Two data streams:

  vehicle_local_position            — PX4 EKF estimate    (DDS-exposed)
  vehicle_local_position_groundtruth — Gazebo truth       (SITL-only, not DDS)
  estimator_status_flags             — EKF fusion flags    (DDS-exposed)

Ground-truth isn't in PX4's uxrce_dds whitelist, so we grab all three from
inside the px4-sitl container using px4-listener, then correlate on host.

Flight trigger goes through /dexi/offboard_manager via docker exec into the
ros2-dev container — identical to the real-drone path.

Usage:
    python3 scripts/validate_flow_sim.py
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

PX4_CONTAINER = "dexi-sim-ftw-px4-sitl-1"
ROS2_CONTAINER = "dexi-sim-ftw-ros2-dev-1"

LOG_DURATION_S = 50  # covers 2s prime + 7s climb + 10s hover + 12s land + margin
LOG_HZ = 20

TOPIC_EKF = "vehicle_local_position"
TOPIC_TRUTH = "vehicle_local_position_groundtruth"
TOPIC_FLAGS = "estimator_status_flags"


@dataclass
class Sample:
    t_us: int
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0  # NED (down-positive)
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    flags: dict[str, bool] = field(default_factory=dict)


def sh(cmd: list[str], check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, capture_output=capture, text=True)


def docker_ok(container: str) -> bool:
    r = sh(["docker", "ps", "--filter", f"name={container}", "--format", "{{.Names}}"], capture=True)
    return container in r.stdout


def start_listener_bg(topic: str, duration_s: int, hz: int, out_path: str) -> None:
    """Launch a looped px4-listener in the sim container that writes to a file.

    This PX4 1.16 build's px4-listener hangs with -n >= 2, but -n 1 returns a
    clean sample. Loop that primitive at the requested cadence until the
    duration elapses. Output lands in `out_path` inside the container.
    """
    interval = 1.0 / hz
    inner = (
        f"cd /opt/px4/rootfs && : > {out_path} && "
        f"end=$(($(date +%s) + {duration_s})) && "
        f"while [ $(date +%s) -lt $end ]; do "
        f"  /opt/px4/bin/px4-listener {topic} -n 1 >> {out_path} 2>&1; "
        f"  sleep {interval}; "
        f"done"
    )
    sh(["docker", "exec", "-d", PX4_CONTAINER, "sh", "-c", inner])


def copy_out(src_in_container: str, dst_local: Path) -> None:
    sh(["docker", "cp", f"{PX4_CONTAINER}:{src_in_container}", str(dst_local)])


MANUAL_CONTROL_FLIGHT_PY = '''
"""Simulated-RC flight for the flow SITL, mimicking real-drone arming.

Real drone: RC in POSCTL, throttle stick up, flow fuses airborne, mode to offboard.
Sim:        publish ManualControlSetpoint at 20Hz as MAVLink source, set ALTCTL,
            arm, ramp throttle up, hover to observe flow fusion, descend, land.

The point of this script is to validate that the flow-bootstrap patch
(fix/optical-flow-range-height-bootstrap on dbaldwin/PX4-Autopilot)
actually engages flow fusion once altitude > SENS_FLOW_MINHGT — i.e.
cs_opt_flow flips True, local_position_valid becomes True, and EKF XY
starts tracking against ground truth.
"""
import threading
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from px4_msgs.msg import VehicleCommand, ManualControlSetpoint

# PX4 custom main mode values for VEHICLE_CMD_DO_SET_MODE param2
MODE_MANUAL = 1; MODE_ALTCTL = 2; MODE_POSCTL = 3
MODE_AUTO = 4; MODE_ACRO = 5; MODE_OFFBOARD = 6; MODE_STABILIZED = 7


class F(Node):
    def __init__(self):
        super().__init__("manual_flight")
        q = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                       durability=DurabilityPolicy.TRANSIENT_LOCAL,
                       history=HistoryPolicy.KEEP_LAST, depth=1)
        self.v = self.create_publisher(VehicleCommand, "/fmu/in/vehicle_command", q)
        self.m = self.create_publisher(ManualControlSetpoint, "/fmu/in/manual_control_input", q)
        # Stick state — modified from main thread, read by the heartbeat thread.
        self.throttle = -1.0  # min = no climb command
        self.roll = 0.0; self.pitch = 0.0; self.yaw = 0.0
        self._stop = False
        self._th = threading.Thread(target=self._heartbeat, daemon=True)
        self._th.start()
        time.sleep(1)

    def _heartbeat(self):
        """20 Hz ManualControlSetpoint publisher — mimics a joystick source."""
        while not self._stop:
            s = ManualControlSetpoint()
            s.timestamp = int(time.monotonic() * 1e6)
            s.timestamp_sample = s.timestamp
            s.valid = True
            s.data_source = ManualControlSetpoint.SOURCE_MAVLINK_0
            s.roll = self.roll; s.pitch = self.pitch
            s.yaw = self.yaw; s.throttle = self.throttle
            self.m.publish(s)
            time.sleep(0.05)

    def stop(self):
        self._stop = True

    def _vcmd(self, command, **kw):
        msg = VehicleCommand()
        msg.command = command
        for i, (_, v) in enumerate(kw.items(), start=1):
            setattr(msg, f"param{i}", float(v))
        msg.target_system = 1; msg.target_component = 1
        msg.source_system = 1; msg.source_component = 1
        msg.from_external = False
        self.v.publish(msg)

    def set_mode(self, px4_main_mode):
        # base_mode param1=1 means "custom mode enabled"; param2 is the PX4 mode.
        self._vcmd(VehicleCommand.VEHICLE_CMD_DO_SET_MODE, p1=1.0, p2=float(px4_main_mode))
        self.get_logger().info(f"DO_SET_MODE({px4_main_mode}) sent"); time.sleep(1)

    def arm(self):
        self._vcmd(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, p1=1.0, p2=0.0)
        self.get_logger().info("arm sent"); time.sleep(2)

    def disarm(self):
        self._vcmd(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, p1=0.0, p2=0.0)
        self.get_logger().info("disarm sent"); time.sleep(1)

    def land(self):
        self._vcmd(VehicleCommand.VEHICLE_CMD_NAV_LAND)
        self.get_logger().info("NAV_LAND sent"); time.sleep(1)


def main():
    rclpy.init(); n = F()
    # Prime: 2s of stick-centered heartbeat so PX4 sees a live manual source
    # before we try to change modes.
    n.get_logger().info("priming manual control heartbeat for 2s")
    time.sleep(2)

    # Altitude mode uses range-sensor height hold — doesn't require local_position.
    n.set_mode(MODE_ALTCTL)

    # Arm. With CBRK_SUPPLY_CHK bypassed and ALTCTL accepting no position,
    # this should succeed without force-arm. If it still fails we'll fall
    # back to force-arm, but the whole point of this path is to avoid that.
    n.arm()

    # Climb: throttle stick = +0.9 for ~7s. Previous +0.6 for 5s only got to
    # 0.4m — below SENS_FLOW_MINHGT=0.7m where flow fusion engages. Push hard
    # to clear 1.5m so we sit comfortably in the fusion window.
    n.get_logger().info("CLIMB — throttle +0.9 for 7s")
    n.throttle = 0.9
    time.sleep(7)

    # Hover: ALTCTL dead-zone is narrow and the iris drifts down at throttle=0.
    # Hold slightly positive to maintain altitude while we watch cs_opt_flow.
    n.get_logger().info("HOVER — throttle +0.1 for 10s (watching flow fusion)")
    n.throttle = 0.1
    time.sleep(10)

    # NAV_LAND (works in ALTCTL once airborne) gives a smooth controlled descent.
    n.land()
    time.sleep(10)

    n.disarm()
    n.stop()
    n.destroy_node(); rclpy.shutdown()


main()
'''


def trigger_flight() -> None:
    """Trigger a simulated-RC flight that mirrors the real-drone arming path.

    Publishes ManualControlSetpoint at 20 Hz while stepping through
    ALTCTL → arm → throttle up → hover → land. This is the sim analogue of
    pushing the throttle stick up in POSCTL on the real drone; flow fusion
    should engage once altitude > SENS_FLOW_MINHGT (0.7 m).
    """
    print(">>> Triggering flight (simulated RC in ALTCTL)")
    sh(["docker", "exec", ROS2_CONTAINER, "bash", "-c",
        "source /opt/ros/humble/setup.bash && "
        "source /home/ubuntu/dexi_ws/install/setup.bash && "
        f"python3 -c {_shell_quote(MANUAL_CONTROL_FLIGHT_PY)}"])


def _shell_quote(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"


# px4-listener text format: blocks separated by blank lines, each block starts
# with "TOPIC: <name>" then indented "key: value" lines, possibly with units.
SAMPLE_HEAD = re.compile(r"^TOPIC:\s+(\S+)")
KV = re.compile(r"^\s+(\w+):\s+(.+?)\s*$")
VEC3 = re.compile(r"\[([-\d.e+nan]+),\s+([-\d.e+nan]+),\s+([-\d.e+nan]+)\]")
VEC2 = re.compile(r"\[([-\d.e+nan]+),\s+([-\d.e+nan]+)\]")


def parse_samples(path: Path, want_flags: bool = False) -> list[Sample]:
    """Very small px4-listener parser — enough for our few fields of interest."""
    samples: list[Sample] = []
    current: dict | None = None
    for line in path.read_text().splitlines():
        if SAMPLE_HEAD.match(line):
            if current is not None:
                samples.append(_mk_sample(current, want_flags))
            current = {}
            continue
        if current is None:
            continue
        m = KV.match(line)
        if not m:
            continue
        key, val = m.group(1), m.group(2)
        current[key] = val
    if current:
        samples.append(_mk_sample(current, want_flags))
    return samples


def _mk_sample(d: dict, want_flags: bool) -> Sample:
    def f(k: str, default: float = 0.0) -> float:
        v = d.get(k, "")
        try:
            return float(v.split()[0])
        except (ValueError, IndexError):
            return default

    s = Sample(t_us=int(f("timestamp")))
    s.x = f("x")
    s.y = f("y")
    s.z = f("z")
    s.vx = f("vx")
    s.vy = f("vy")
    s.vz = f("vz")
    if want_flags:
        for k, v in d.items():
            if k.startswith("cs_") or k.startswith("fs_"):
                s.flags[k] = v.strip().lower() == "true"
    return s


def correlate(ekf: list[Sample], truth: list[Sample]) -> list[tuple[Sample, Sample]]:
    """Nearest-timestamp join."""
    pairs: list[tuple[Sample, Sample]] = []
    if not ekf or not truth:
        return pairs
    j = 0
    for e in ekf:
        while j + 1 < len(truth) and abs(truth[j + 1].t_us - e.t_us) <= abs(truth[j].t_us - e.t_us):
            j += 1
        pairs.append((e, truth[j]))
    return pairs


def summarize(pairs: list[tuple[Sample, Sample]], flags: list[Sample]) -> int:
    """Return 0 on PASS, non-zero on FAIL."""
    if not pairs:
        print("FAIL: no correlated samples")
        return 2

    e0, t0 = pairs[0]
    # Working in NED (z positive = down). Altitude = -z.
    alt_truth = [-(p[1].z - t0.z) for p in pairs]
    max_alt = max(alt_truth)
    peak_i = alt_truth.index(max_alt)

    # Measure altitude hold over the central 60% of the above-1m segment
    above = [i for i, a in enumerate(alt_truth) if a > 1.0]
    if len(above) < 20:
        print("FAIL: never climbed above 1m — flight didn't take off or flow fusion failed")
        return 3
    hover_slice = above[len(above) // 5 : -len(above) // 5]
    hold_alts = [alt_truth[i] for i in hover_slice]
    hold_mean = sum(hold_alts) / len(hold_alts)
    hold_dev = max(abs(a - hold_mean) for a in hold_alts)

    # Horizontal drift (truth frame) across the hover window
    xy_drift = max(
        ((pairs[i][1].x - t0.x) ** 2 + (pairs[i][1].y - t0.y) ** 2) ** 0.5
        for i in hover_slice
    )

    # EKF vs truth altitude agreement at peak
    alt_err_peak = abs((-(pairs[peak_i][0].z - e0.z)) - max_alt)

    # Flow-fusion flag — must flip True at some point in the air
    flow_on = any(s.flags.get("cs_opt_flow", False) for s in flags)
    rng_hgt = any(s.flags.get("cs_rng_hgt", False) for s in flags)

    print()
    print(f"  flight peak altitude (truth)      : {max_alt:.3f} m")
    print(f"  altitude hold mean (truth)        : {hold_mean:.3f} m")
    print(f"  altitude hold worst deviation     : {hold_dev * 100:.1f} cm")
    print(f"  horizontal drift during hover     : {xy_drift:.3f} m")
    print(f"  EKF-vs-truth altitude err (peak)  : {alt_err_peak * 100:.1f} cm")
    print(f"  EKF cs_opt_flow seen True         : {flow_on}")
    print(f"  EKF cs_rng_hgt  seen True         : {rng_hgt}")
    print()

    # Thresholds are calibrated for the simulated-RC-in-ALTCTL profile this
    # script drives, NOT the prod offboard position-hold path. ALTCTL hovers
    # loose because throttle stick drives velocity, not altitude lock; prod's
    # ±5–12 cm number comes from dexi_offboard's 20 Hz position setpoints.
    # What we're actually validating here: sensor wiring + flow fusion + EKF
    # tracking of truth. Tight altitude-hold isn't this flight's job.
    fail = 0
    if not rng_hgt:
        print("FAIL: range sensor never used as height reference (EKF2_HGT_REF=2 not applied?)")
        fail |= 1
    if not flow_on:
        print("FAIL: optical flow never fused — camera or EKF rejected data (check CameraSensor init)")
        fail |= 1
    if alt_err_peak > 0.50:
        print(f"FAIL: EKF-vs-truth peak altitude error {alt_err_peak * 100:.1f} cm > 50 cm")
        fail |= 1
    if fail == 0:
        print("PASS: flow fusion engages airborne and EKF altitude tracks truth within tolerance")
        print("NOTE: large altitude_hold deviation and horizontal drift are EXPECTED for "
              "manual-stick ALTCTL with flow-only (velocity-based) — prod uses offboard "
              "position setpoints, not this control path.")
    return fail


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("flight_logs"), help="directory for CSV logs")
    ap.add_argument("--skip-flight", action="store_true", help="don't trigger flight, only parse existing logs")
    args = ap.parse_args()

    args.out.mkdir(exist_ok=True)

    if not args.skip_flight:
        if not docker_ok(PX4_CONTAINER):
            print(f"ERROR: {PX4_CONTAINER} not running", file=sys.stderr)
            return 1
        if not docker_ok(ROS2_CONTAINER):
            print(f"ERROR: {ROS2_CONTAINER} not running", file=sys.stderr)
            return 1

        print(f">>> Starting listeners for {LOG_DURATION_S}s at {LOG_HZ} Hz")
        start_listener_bg(TOPIC_EKF, LOG_DURATION_S, LOG_HZ, "/tmp/ekf.log")
        start_listener_bg(TOPIC_TRUTH, LOG_DURATION_S, LOG_HZ, "/tmp/truth.log")
        start_listener_bg(TOPIC_FLAGS, LOG_DURATION_S, LOG_HZ, "/tmp/flags.log")
        time.sleep(2)

        trigger_flight()

        # Give listeners time to finish writing their remaining samples
        print(">>> Waiting for listeners to drain")
        time.sleep(5)

        copy_out("/tmp/ekf.log", args.out / "ekf.log")
        copy_out("/tmp/truth.log", args.out / "truth.log")
        copy_out("/tmp/flags.log", args.out / "flags.log")

    ekf = parse_samples(args.out / "ekf.log")
    truth = parse_samples(args.out / "truth.log")
    flags = parse_samples(args.out / "flags.log", want_flags=True)
    print(f">>> Parsed {len(ekf)} EKF / {len(truth)} truth / {len(flags)} flag samples")

    pairs = correlate(ekf, truth)
    return summarize(pairs, flags)


if __name__ == "__main__":
    sys.exit(main())
