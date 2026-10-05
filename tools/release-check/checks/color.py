# Fly over each DEXI Lab color pad at 1 m and confirm /color_detections reports that color.
import rclpy, time
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from dexi_interfaces.srv import ExecuteBlocklyCommand
from dexi_interfaces.msg import ColorDetectionArray
from px4_msgs.msg import VehicleLocalPosition
rclpy.init(); n = Node('color_check'); st = {}; seen = []
n.create_subscription(VehicleLocalPosition, '/fmu/out/vehicle_local_position', lambda m: st.update(x=m.x, y=m.y, z=m.z, yaw=m.heading), qos_profile_sensor_data)
n.create_subscription(ColorDetectionArray, '/color_detections', lambda m: seen.append([(d.color_name, round(d.confidence, 2), d.pixel_count) for d in m.detections]), 10)
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
z = st['z']; yaw = st['yaw'] * 57.2958
results = {}
for name, east in [('red', -0.4), ('orange', 0.8), ('yellow', 2.0), ('green', 3.2), ('blue', 4.4)]:
    call('goto_ned', north=-1.5, east=east, down=z, yaw=yaw); spin(2.5)
    seen.clear(); spin(2.0)
    names = sorted({c for frame in seen for (c, _, _) in frame})
    best = max((d for frame in seen for d in frame if d[0] == name), key=lambda d: d[2], default=None)
    results[name] = (name in names, names, best)
    print(f'{name:7s} over pad at ({-1.5}, {east}): detected {names}  best match {best}  [{len(seen)} frames]', flush=True)
call('goto_ned', north=0, east=0, down=z, yaw=yaw); spin(2); call('land'); spin(8)
ok = all(v[0] for v in results.values())
print('COLOR DETECTION:', 'PASS' if ok else 'FAIL', {k: v[0] for k, v in results.items()}, flush=True)
