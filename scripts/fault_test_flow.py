#!/usr/bin/env python3
"""Fault-injection teaching exercise: lose optical flow while holding
position in POSCTL mode.

Takeoff in POSCTL isn't possible from the ground — PX4 requires
local_position_valid, which only comes online once flow engages above
~0.7 m. So the flight starts in ALTCTL, climbs above the flow threshold,
then switches to POSCTL where horizontal position is actively held.

Sequence:
  0 s   listeners start
  2 s   flight begins
  3 s   ALTCTL + arm
  5 s   climb (throttle +0.9, 7 s)
 12 s   ALTCTL hover — flow engages, local_position becomes valid
 15 s   SWITCH to POSCTL — drone actively holds position using flow
 15-25  POSCTL baseline — drone should be rock-steady (no drift)
 25 s   FAULT: EKF2_OF_CTRL = 0 — stop fusing optical flow
 25-40  Observe: EKF position estimate drifts, POSCTL chases the bad
        estimate, drone visibly drifts away from its position setpoint
 40 s   NAV_LAND
 ~52 s  disarm

Flow is our only horizontal position aid (no GPS, no external vision).
Killing it while POSCTL is actively relying on it is a dramatic visible
failure, unlike the same fault in ALTCTL which doesn't use horizontal
position.

Expected behavior:
- `cs_opt_flow` → False within ~1 s of fault
- `cs_inertial_dead_reckoning` → True
- Altitude stays clean (range + baro still fusing)
- POSCTL may remain active or auto-fall-back depending on PX4 internals
- Physical XY drift: probably 2–5 m over 15 s post-fault
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

LOG_DURATION_S = 65
LOG_HZ = 20
FAULT_AT_S = 25  # 10 s into POSCTL hover, after 3 s of baseline

MANUAL_FLIGHT_PY = '''
import threading, time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from px4_msgs.msg import VehicleCommand, ManualControlSetpoint

MODE_ALTCTL = 2
MODE_POSCTL = 3

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
    n.throttle = 0.9; time.sleep(7)     # climb to ~4 m
    n.throttle = 0.1; time.sleep(3)     # brief ALTCTL hover — flow engages
    n.throttle = 0.0                    # neutral stick for POSCTL transition
    n.set_mode(MODE_POSCTL)             # now actively holding x/y via flow
    time.sleep(25)                      # baseline 10s + post-fault 15s
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
    eph: float = 0.0
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
    print(f"\n>>> INJECTING FAULT: EKF2_OF_CTRL = 0 (disable flow fusion)\n")
    sh(["docker", "exec", PX4_CONTAINER, "sh", "-c",
        "cd /opt/px4/rootfs && /opt/px4/bin/px4-param set EKF2_OF_CTRL 0"])


def restore_fault() -> None:
    sh(["docker", "exec", PX4_CONTAINER, "sh", "-c",
        "cd /opt/px4/rootfs && /opt/px4/bin/px4-param set EKF2_OF_CTRL 1"])


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

    s = Sample(t_us=int(f("timestamp")), x=f("x"), y=f("y"), z=f("z"), eph=f("eph"))
    if want_flags:
        for k, v in d.items():
            if k.startswith("cs_") or k.startswith("fs_"):
                s.flags[k] = v.strip().lower() == "true"
    return s


def nearest(arr, t):
    return min(arr, key=lambda s: abs(s.t_us - t))


def main() -> int:
    out = Path("flight_logs_fault_flow")
    out.mkdir(exist_ok=True)

    print(f">>> Starting listeners for {LOG_DURATION_S}s at {LOG_HZ} Hz")
    start_listener_bg("vehicle_local_position",
                      LOG_DURATION_S, LOG_HZ, "/tmp/ekf.log")
    start_listener_bg("vehicle_local_position_groundtruth",
                      LOG_DURATION_S, LOG_HZ, "/tmp/truth.log")
    start_listener_bg("estimator_status_flags",
                      LOG_DURATION_S, LOG_HZ, "/tmp/flags.log")
    time.sleep(2)

    t_start = time.monotonic()
    print(">>> Triggering flight (simulated RC in ALTCTL)")
    flight = subprocess.Popen(
        ["docker", "exec", ROS2_CONTAINER, "bash", "-c",
         "source /opt/ros/humble/setup.bash && "
         "source /home/ubuntu/dexi_ws/install/setup.bash && "
         f"python3 -c {_shq(MANUAL_FLIGHT_PY)}"],
        stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    def fire():
        elapsed = time.monotonic() - t_start
        time.sleep(max(0, FAULT_AT_S - elapsed))
        inject_fault()

    threading.Thread(target=fire, daemon=True).start()

    flight.wait()
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
    x0t, y0t = truth[0].x, truth[0].y
    x0e, y0e = ekf[0].x, ekf[0].y
    z0t, z0e = truth[0].z, ekf[0].z

    def alt(s, z0): return -(s.z - z0)
    def xy_err(e, t):
        return ((e.x - x0e - (t.x - x0t)) ** 2 +
                (e.y - y0e - (t.y - y0t)) ** 2) ** 0.5

    checkpoints = [
        ("ALTCTL climb done (t=14s)", 14),
        ("POSCTL entered, baseline (t=20s)", 20),
        ("fault moment (t=25s)", 25),
        ("post-fault +1s", 26),
        ("post-fault +3s", 28),
        ("post-fault +5s", 30),
        ("post-fault +10s", 35),
        ("post-fault +15s (~NAV_LAND)", 40),
    ]
    print()
    for label, tgt in checkpoints:
        t = t0 + int(tgt * 1e6)
        e = nearest(ekf, t); tr = nearest(truth, t); fl = nearest(flags, t)
        print(f"  {label}:")
        print(f"    alt truth {alt(tr, z0t):5.2f}m  EKF {alt(e, z0e):5.2f}m  "
              f"alt_err {abs(alt(e, z0e) - alt(tr, z0t))*100:4.1f}cm")
        print(f"    xy_err EKF-vs-truth {xy_err(e, tr):5.2f}m  "
              f"eph {e.eph:.2f}m  "
              f"opt_flow={fl.flags.get('cs_opt_flow')}  "
              f"dead_rck={fl.flags.get('cs_inertial_dead_reckoning')}  "
              f"rng_hgt={fl.flags.get('cs_rng_hgt')}  "
              f"baro_hgt={fl.flags.get('cs_baro_hgt')}")

    return 0


def _shq(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"


if __name__ == "__main__":
    sys.exit(main())
