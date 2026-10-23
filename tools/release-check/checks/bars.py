# Fly over the DEXI Lab bridge stickers and one barrel at 0.6 m and read /bar_detections.
# Pass = each bridge reads its bar count and the barrel publishes nothing.
import rclpy, time, sys
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from dexi_interfaces.srv import ExecuteBlocklyCommand
from dexi_interfaces.msg import YoloDetectionArray
from px4_msgs.msg import VehicleLocalPosition
ALT = float(sys.argv[1]) if len(sys.argv) > 1 else 0.6
# Index is the sticker's slot in the DEXI Lab row, as in yolo.py.
EXPECT = [(0, 'wheat', None), (7, 'bridge_1', 'bars_1'), (8, 'bridge_2', 'bars_2'), (9, 'bridge_3', 'bars_3')]
rclpy.init(); n = Node('bars_check'); st = {}; seen = []
n.create_subscription(VehicleLocalPosition, '/fmu/out/vehicle_local_position', lambda m: st.update(x=m.x, y=m.y, z=m.z, yaw=m.heading), qos_profile_sensor_data)
n.create_subscription(YoloDetectionArray, '/bar_detections', lambda m: seen.append([d.class_name for d in m.detections]), 10)
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
z0 = st['z'] + 1.0
yaw = st['yaw'] * 57.2958; ok_count = 0
for i, sticker, cls in EXPECT:
    east = 2.0 + (i - 4.5) * 0.6
    call("goto_ned", north=5.5, east=east, down=z0 - ALT, yaw=yaw); call("hold_ned", north=5.5, east=east, down=z0 - ALT, yaw=yaw); spin(5)
    seen.clear(); spin(5)                            # 2 Hz with a 3-of-5 vote: a few published answers
    got = sorted({c for fr in seen for c in fr})
    ok = got == ([cls] if cls else []); ok_count += ok
    print(f'{sticker:9s} at (5.5, {east:.1f}) {ALT} m: expect {cls} got {got} [{len(seen)} msgs] {"OK" if ok else "MISS"}', flush=True)
call('goto_ned', north=0, east=0, down=z0 - 1.0, yaw=yaw); spin(2); call('land'); spin(8)
print(f'BARS: {ok_count}/{len(EXPECT)} stickers read correctly at {ALT} m', flush=True)
