#!/usr/bin/env python3
"""Fault-injection teaching exercise: remove ALL height sources mid-hover.

Sequence:
  0 s  start listeners
  2 s  flight begins, climb in ALTCTL to ~4 m
 15 s  drone stable in hover, flow + range + baro all fused
 22 s  FAULT: EKF2_RNG_CTRL = 0 AND EKF2_BARO_CTRL = 0 simultaneously
 36 s  NAV_LAND (if the drone is still where we expect it)
 ~48 s disarm

With no direct altitude measurement of any kind, the EKF can only
integrate vertical accelerometer readings to maintain altitude. Even
~0.01 m/s^2 accel bias becomes ~50 cm of position error after 10 s —
unbounded drift.

Expected outcomes (any of these is a valid teaching outcome):

  1. EKF altitude estimate diverges from truth at 5–30 cm/s. Controller
     chases the estimate, drone physically drifts in altitude —
     visibly up or down within 5 s.

  2. PX4 commander detects local_alt_valid going False, fails over to
     AUTO_LAND or terminates.

  3. `cs_baro_fault` triggers from a large post-disable innovation,
     EKF goes into degraded mode.

Compare to the range-only fault where baro took over cleanly — this
version has nothing to take over.
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
FAULT_AT_S = 22

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
    time.sleep(2)
    n.set_mode(MODE_ALTCTL)
    n.arm()
    n.throttle = 0.9; time.sleep(7)
    n.throttle = 0.1; time.sleep(20)   # long hover — fault hits ~6s in
    n.land(); time.sleep(12)
    n.disarm(); time.sleep(1)
    n._stop = True
    n.destroy_node(); rclpy.shutdown()

main()
'''


@dataclass
class Sample:
    t_us: int
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
    """Kill both height sources at once. No graceful fallback possible."""
    print(f"\n>>> INJECTING FAULT: EKF2_RNG_CTRL = 0 AND EKF2_BARO_CTRL = 0\n")
    sh(["docker", "exec", PX4_CONTAINER, "sh", "-c",
        "cd /opt/px4/rootfs && "
        "/opt/px4/bin/px4-param set EKF2_RNG_CTRL 0 && "
        "/opt/px4/bin/px4-param set EKF2_BARO_CTRL 0"])


def restore_fault() -> None:
    """Reset both params so the sim is clean for the next run."""
    sh(["docker", "exec", PX4_CONTAINER, "sh", "-c",
        "cd /opt/px4/rootfs && "
        "/opt/px4/bin/px4-param set EKF2_RNG_CTRL 2 && "
        "/opt/px4/bin/px4-param set EKF2_BARO_CTRL 1"])


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

    s = Sample(t_us=int(f("timestamp")), z=f("z"))
    if want_flags:
        for k, v in d.items():
            if k.startswith("cs_") or k.startswith("fs_"):
                s.flags[k] = v.strip().lower() == "true"
    return s


def nearest(arr, t):
    return min(arr, key=lambda s: abs(s.t_us - t))


def main() -> int:
    out = Path("flight_logs_no_height")
    out.mkdir(exist_ok=True)

    print(f">>> Starting listeners for {LOG_DURATION_S}s at {LOG_HZ} Hz")
    start_listener_bg("vehicle_local_position",
                      LOG_DURATION_S, LOG_HZ, "/tmp/ekf.log")
    start_listener_bg("vehicle_local_position_groundtruth",
                      LOG_DURATION_S, LOG_HZ, "/tmp/truth.log")
    start_listener_bg("estimator_status_flags",
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

    def fire_fault():
        elapsed = time.monotonic() - t_listener_start
        time.sleep(max(0, FAULT_AT_S - elapsed))
        inject_fault()

    threading.Thread(target=fire_fault, daemon=True).start()

    flight_proc.wait()
    print(">>> Flight done — draining listeners")
    time.sleep(3)
    restore_fault()

    for name in ("ekf", "truth", "flags"):
        copy_out(f"/tmp/{name}.log", out / f"{name}.log")

    ekf = parse_samples(out / "ekf.log")
    truth = parse_samples(out / "truth.log")
    flags = parse_samples(out / "flags.log", want_flags=True)
    print(f">>> Parsed {len(ekf)}/{len(truth)}/{len(flags)} samples")
    if not (ekf and truth and flags):
        print("FAIL: no samples captured")
        return 1

    t0 = truth[0].t_us
    z0_truth = truth[0].z
    z0_ekf = ekf[0].z

    def alt(s: Sample, z0: float) -> float:
        return -(s.z - z0)

    # Sample the altitude trajectory and flag state at key moments
    checkpoints = [
        ("pre-fault (t=20s)", 20),
        ("fault moment (t=22s)", 22),
        ("post-fault +1s", 23),
        ("post-fault +3s", 25),
        ("post-fault +5s", 27),
        ("post-fault +8s", 30),
        ("post-fault +12s", 34),
    ]
    print()
    for label, tgt_s in checkpoints:
        t = t0 + int(tgt_s * 1e6)
        e = nearest(ekf, t); tr = nearest(truth, t); fl = nearest(flags, t)
        print(f"  {label}:")
        print(f"    truth {alt(tr, z0_truth):6.2f}m  EKF {alt(e, z0_ekf):6.2f}m  "
              f"err {abs(alt(e, z0_ekf) - alt(tr, z0_truth))*100:5.1f}cm")
        print(f"    rng_hgt={fl.flags.get('cs_rng_hgt')}  "
              f"baro_hgt={fl.flags.get('cs_baro_hgt')}  "
              f"opt_flow={fl.flags.get('cs_opt_flow')}  "
              f"dead_rck={fl.flags.get('cs_inertial_dead_reckoning')}  "
              f"baro_fault={fl.flags.get('cs_baro_fault')}  "
              f"rng_fault={fl.flags.get('cs_rng_fault')}")

    return 0


def _shq(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"


if __name__ == "__main__":
    sys.exit(main())
