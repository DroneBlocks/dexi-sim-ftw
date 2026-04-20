#!/usr/bin/env python3
"""Fault-injection teaching exercise: lose the range sensor mid-hover.

Sequence:
  0 s  start listeners
  2 s  flight begins, climb in ALTCTL to ~4 m
 15 s  drone stable in hover, flow + range both fused
 20 s  FAULT: `EKF2_RNG_CTRL = 0` — stop fusing range measurements
 35 s  NAV_LAND
 ~45 s disarm

During the fault window we expect one of three outcomes, all worth
observing:

  A) Baro takes over cleanly. Sim baro is accurate enough that altitude
     estimate converges ~20-50 cm off truth and drone holds altitude.
     Contrast with real drone where indoor baro drifts meters and this
     would be an emergency.

  B) EKF declares unhealthy, commander fails over to AUTO_LAND. The
     drone descends on its own.

  C) Flow fusion disengages because HAGL becomes unknown, horizontal
     drift accelerates, eventually the whole estimate collapses.

We plot ground-truth altitude vs EKF altitude, and flag transitions,
split by the fault moment — so students see exactly which outcome
occurred and when.
"""

from __future__ import annotations

import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

PX4_CONTAINER = "dexi-sim-ftw-px4-sitl-1"
ROS2_CONTAINER = "dexi-sim-ftw-ros2-dev-1"

LOG_DURATION_S = 60
LOG_HZ = 20

# Wall-clock offset, measured from the moment this host script starts its
# listeners, at which we inject the fault. Flight script starts 2s after
# listeners, then: 2s prime + 1s mode + 2s arm + 7s climb = airborne at ~14s,
# hover stable by ~16s. Inject at 22s = 6s into the hover.
FAULT_AT_S = 22

# Flight inner script — simulated RC in ALTCTL, longer hover window so we
# have time to observe the post-fault behavior before landing.
MANUAL_FLIGHT_PY = '''
import threading, time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from px4_msgs.msg import VehicleCommand, ManualControlSetpoint

MODE_ALTCTL = 2

class F(Node):
    def __init__(self):
        super().__init__("fault_flight")
        q = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                       durability=DurabilityPolicy.TRANSIENT_LOCAL,
                       history=HistoryPolicy.KEEP_LAST, depth=1)
        self.v = self.create_publisher(VehicleCommand, "/fmu/in/vehicle_command", q)
        self.m = self.create_publisher(ManualControlSetpoint, "/fmu/in/manual_control_input", q)
        self.throttle = -1.0
        self.roll = self.pitch = self.yaw = 0.0
        self._stop = False
        self._th = threading.Thread(target=self._heartbeat, daemon=True)
        self._th.start()
        time.sleep(1)

    def _heartbeat(self):
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

    def _vcmd(self, command, **kw):
        msg = VehicleCommand()
        msg.command = command
        for i, (_, v) in enumerate(kw.items(), start=1):
            setattr(msg, f"param{i}", float(v))
        msg.target_system = 1; msg.target_component = 1
        msg.source_system = 1; msg.source_component = 1
        msg.from_external = False
        self.v.publish(msg)

    def set_mode(self, m):
        self._vcmd(VehicleCommand.VEHICLE_CMD_DO_SET_MODE, p1=1.0, p2=float(m))
        time.sleep(1)
    def arm(self):
        self._vcmd(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, p1=1.0, p2=0.0)
        time.sleep(2)
    def disarm(self):
        self._vcmd(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, p1=0.0, p2=0.0)
    def land(self):
        self._vcmd(VehicleCommand.VEHICLE_CMD_NAV_LAND)

def main():
    rclpy.init(); n = F()
    time.sleep(2)            # prime heartbeat
    n.set_mode(MODE_ALTCTL)
    n.arm()
    n.throttle = 0.9; time.sleep(7)     # climb
    n.throttle = 0.1; time.sleep(20)    # long hover — fault lands ~6s in
    n.land(); time.sleep(12)
    n.disarm(); time.sleep(1)
    n._stop = True
    n.destroy_node(); rclpy.shutdown()

main()
'''


@dataclass
class Sample:
    t_us: int
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    flags: dict[str, bool] = field(default_factory=dict)


def sh(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True)


def start_listener_bg(topic: str, duration_s: int, hz: int, out_path: str) -> None:
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


def copy_out(src: str, dst: Path) -> None:
    sh(["docker", "cp", f"{PX4_CONTAINER}:{src}", str(dst)])


def inject_fault() -> None:
    """Disable range fusion in the running PX4. Instantaneous, no reboot."""
    print(f"\n>>> INJECTING FAULT: EKF2_RNG_CTRL = 0\n")
    sh(["docker", "exec", PX4_CONTAINER, "sh", "-c",
        "cd /opt/px4/rootfs && /opt/px4/bin/px4-param set EKF2_RNG_CTRL 0"])


def restore_fault() -> None:
    """Return EKF2_RNG_CTRL to prod value so the next run starts clean."""
    sh(["docker", "exec", PX4_CONTAINER, "sh", "-c",
        "cd /opt/px4/rootfs && /opt/px4/bin/px4-param set EKF2_RNG_CTRL 2"])


SAMPLE_HEAD = re.compile(r"^TOPIC:\s+(\S+)")
KV = re.compile(r"^\s+(\w+):\s+(.+?)\s*$")


def parse_samples(path: Path, want_flags: bool = False) -> list[Sample]:
    samples: list[Sample] = []
    current: dict | None = None
    for line in path.read_text().splitlines():
        if SAMPLE_HEAD.match(line):
            if current is not None:
                samples.append(_mk(current, want_flags))
            current = {}
            continue
        if current is None:
            continue
        m = KV.match(line)
        if m:
            current[m.group(1)] = m.group(2)
    if current:
        samples.append(_mk(current, want_flags))
    return samples


def _mk(d: dict, want_flags: bool) -> Sample:
    def f(k: str) -> float:
        try:
            return float(d.get(k, "0").split()[0])
        except (ValueError, IndexError):
            return 0.0

    s = Sample(t_us=int(f("timestamp")))
    s.x = f("x"); s.y = f("y"); s.z = f("z")
    if want_flags:
        for k, v in d.items():
            if k.startswith("cs_") or k.startswith("fs_"):
                s.flags[k] = v.strip().lower() == "true"
    return s


def window_stats(pairs: list[tuple[Sample, Sample]], t0: Sample, t1: Sample,
                 fault_t_us: int, window: str) -> dict:
    """Stats over the pre-fault or post-fault window."""
    if window == "pre":
        sub = [(e, t) for e, t in pairs if e.t_us < fault_t_us]
    else:
        sub = [(e, t) for e, t in pairs if e.t_us >= fault_t_us]
    if not sub:
        return {}
    # Altitude = -z (NED z+ is down)
    alt_truth = [-(t.z - t0.z) for _, t in sub]
    alt_ekf = [-(e.z - t1.z) for e, _ in sub]
    alt_err = [abs(a - b) for a, b in zip(alt_ekf, alt_truth)]
    return {
        "n": len(sub),
        "truth_mean": sum(alt_truth) / len(alt_truth),
        "truth_dev": max(alt_truth) - min(alt_truth),
        "err_mean_cm": 100 * sum(alt_err) / len(alt_err),
        "err_max_cm": 100 * max(alt_err),
    }


def flag_transitions(flags: list[Sample], key: str) -> list[tuple[int, bool]]:
    transitions = []
    prev = None
    for s in flags:
        v = s.flags.get(key)
        if v is not None and v != prev:
            transitions.append((s.t_us, v))
            prev = v
    return transitions


def main() -> int:
    out = Path("flight_logs_fault_rng")
    out.mkdir(exist_ok=True)

    print(f">>> Starting listeners for {LOG_DURATION_S}s at {LOG_HZ} Hz")
    start_listener_bg(TOPIC_EKF := "vehicle_local_position",
                      LOG_DURATION_S, LOG_HZ, "/tmp/ekf.log")
    start_listener_bg(TOPIC_TRUTH := "vehicle_local_position_groundtruth",
                      LOG_DURATION_S, LOG_HZ, "/tmp/truth.log")
    start_listener_bg(TOPIC_FLAGS := "estimator_status_flags",
                      LOG_DURATION_S, LOG_HZ, "/tmp/flags.log")
    time.sleep(2)

    t_listener_start = time.monotonic()

    print(">>> Triggering flight (simulated RC in ALTCTL, long hover)")
    flight_proc = subprocess.Popen(
        ["docker", "exec", ROS2_CONTAINER, "bash", "-c",
         "source /opt/ros/humble/setup.bash && "
         "source /home/ubuntu/dexi_ws/install/setup.bash && "
         f"python3 -c {_shq(MANUAL_FLIGHT_PY)}"],
        stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    # Parallel: wait for the fault moment, inject, keep observing.
    def fire_fault():
        elapsed = time.monotonic() - t_listener_start
        time.sleep(max(0, FAULT_AT_S - elapsed))
        inject_fault()

    fault_thread = threading.Thread(target=fire_fault, daemon=True)
    fault_thread.start()

    fault_wall_time_us = (int(time.time() * 1e6) +
                          int((FAULT_AT_S - (time.monotonic() - t_listener_start)) * 1e6))

    flight_proc.wait()
    print(">>> Flight done — draining listeners")
    time.sleep(3)

    # Restore the param so next run starts clean
    restore_fault()

    for topic, name in ((TOPIC_EKF, "ekf"), (TOPIC_TRUTH, "truth"), (TOPIC_FLAGS, "flags")):
        copy_out(f"/tmp/{name}.log", out / f"{name}.log")

    ekf = parse_samples(out / "ekf.log")
    truth = parse_samples(out / "truth.log")
    flags = parse_samples(out / "flags.log", want_flags=True)
    print(f">>> Parsed {len(ekf)}/{len(truth)}/{len(flags)} samples")
    if not (ekf and truth and flags):
        print("FAIL: no samples captured")
        return 1

    # Nearest-timestamp join
    pairs = []
    j = 0
    for e in ekf:
        while j + 1 < len(truth) and abs(truth[j + 1].t_us - e.t_us) <= abs(truth[j].t_us - e.t_us):
            j += 1
        pairs.append((e, truth[j]))

    # The fault time was captured in host wall-clock micros, but PX4 uORB
    # timestamps are relative to PX4 boot. Use the listener sample stream to
    # translate: find the EKF sample whose wall-clock sample we'd see around
    # the fault moment — approximate by fraction of log length.
    fault_frac = FAULT_AT_S / LOG_DURATION_S
    fault_idx = int(len(pairs) * fault_frac)
    fault_t_us = pairs[fault_idx][0].t_us if pairs else 0

    pre = window_stats(pairs, pairs[0][0], pairs[0][1], fault_t_us, "pre")
    post = window_stats(pairs, pairs[0][0], pairs[0][1], fault_t_us, "post")

    print()
    print(f"  FAULT INJECTED at t≈{FAULT_AT_S}s into recording "
          f"(sample {fault_idx}/{len(pairs)})")
    print()
    print(f"{'':25s} {'PRE-fault':>14s}   {'POST-fault':>14s}")
    print(f"  {'samples':22s} {pre['n']:>14d}   {post['n']:>14d}")
    print(f"  {'truth alt mean':22s} {pre['truth_mean']:>13.2f}m   {post['truth_mean']:>13.2f}m")
    print(f"  {'truth alt range':22s} {pre['truth_dev']*100:>12.0f}cm   {post['truth_dev']*100:>12.0f}cm")
    print(f"  {'EKF-vs-truth err mean':22s} {pre['err_mean_cm']:>12.1f}cm   {post['err_mean_cm']:>12.1f}cm")
    print(f"  {'EKF-vs-truth err max':22s} {pre['err_max_cm']:>12.1f}cm   {post['err_max_cm']:>12.1f}cm")

    print()
    print("  EKF fusion flag transitions:")
    for key in ("cs_rng_hgt", "cs_opt_flow", "cs_baro_hgt",
                "cs_inertial_dead_reckoning", "cs_rng_stuck", "cs_rng_fault"):
        tr = flag_transitions(flags, key)
        if tr:
            lineage = " → ".join(str(v) for _, v in tr)
            print(f"    {key:30s} {lineage}")

    return 0


def _shq(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"


if __name__ == "__main__":
    sys.exit(main())
