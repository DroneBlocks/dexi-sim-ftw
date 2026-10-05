# Fly over each AVR 2026 sticker in the DEXI Lab at 0.6 m and read /yolo_detections.
# Bridges 2 and 3 are left out: the model under-counts the lines on the rendered cups
# (see the dexi_yolo issue on bridge line counting). Pass = all eight others detected.
import rclpy, time, sys
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from dexi_interfaces.srv import ExecuteBlocklyCommand
from dexi_interfaces.msg import YoloDetectionArray
from px4_msgs.msg import VehicleLocalPosition
ALT = float(sys.argv[1]) if len(sys.argv) > 1 else 0.6
ONLY = sys.argv[2].split(',') if len(sys.argv) > 2 else None
EXPECT = [('wheat', 'wheat_barrel'), ('water', 'water_barrel'), ('gasoline', 'gasoline'), ('toxic', 'toxic_fluid'), ('blackout', 'blackout'),
          ('wheat_barn', 'wheat_barn'), ('water_barn', 'water_barn'), ('bridge_1', 'bridge_1line'), ('bridge_2', 'bridge_2line'), ('bridge_3', 'bridge_3line')]
rclpy.init(); n = Node('yolo_check'); st = {}; seen = []
n.create_subscription(VehicleLocalPosition, '/fmu/out/vehicle_local_position', lambda m: st.update(x=m.x, y=m.y, z=m.z, yaw=m.heading), qos_profile_sensor_data)
n.create_subscription(YoloDetectionArray, '/yolo_detections', lambda m: seen.append([(d.class_name, round(d.confidence, 2)) for d in m.detections]), 10)
cli = n.create_client(ExecuteBlocklyCommand, '/dexi/execute_blockly_command'); cli.wait_for_service(15.0)
def spin(s):
    t0 = time.time()
    while time.time() - t0 < s: rclpy.spin_once(n, timeout_sec=0.1)
def call(command, parameter=0.0, timeout=40.0, **kw):
    r = ExecuteBlocklyCommand.Request(command=command, parameter=float(parameter), timeout=float(timeout))
    for k, v in kw.items(): setattr(r, k, float(v))
    f = cli.call_async(r)
    while rclpy.ok() and not f.done(): rclpy.spin_once(n, timeout_sec=0.1)
    return f.result()
spin(2); call('start_offboard_heartbeat'); call('arm'); spin(1.5)
print('takeoff:', call('offboard_takeoff', 1.0).message, flush=True)
z0 = st['z'] + 1.0                                   # floor in EKF frame, roughly
yaw = st['yaw'] * 57.2958; hits = 0
for i, (sticker, cls) in enumerate(EXPECT):
    if ONLY and sticker not in ONLY: continue
    east = 2.0 + (i - 4.5) * 0.6
    call("goto_ned", north=5.5, east=east, down=z0 - ALT, yaw=yaw); call("hold_ned", north=5.5, east=east, down=z0 - ALT, yaw=yaw); spin(5)
    seen.clear(); spin(4.5)                          # YOLO runs at 1 Hz: four or five frames
    got = sorted({c for fr in seen for (c, _) in fr}); best = max((cf for fr in seen for (c, cf) in fr if c == cls), default=None)
    ok = cls in got; hits += ok
    print(f'{sticker:11s} at ({5.5}, {east:.1f}) {ALT} m: expect {cls:13s} got {got} best {best} [{len(seen)} frames] {"OK" if ok else "MISS"}', flush=True)
call('goto_ned', north=0, east=0, down=z0 - 1.0, yaw=yaw); spin(2); call('land'); spin(8)
print(f'YOLO: {hits}/{len(ONLY) if ONLY else len(EXPECT)} classes detected at {ALT} m', flush=True)
