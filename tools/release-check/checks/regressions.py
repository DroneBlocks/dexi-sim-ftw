# Two regressions caught on 2026-10-04, run with rclpy inside the ROS container:
#  1. arm on the ground, then disarm (PX4 must stay "landed" under the manager's ground hold)
#  2. a hold_ned mission, land, then a new takeoff must report arrival
import rclpy, time
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from dexi_interfaces.srv import ExecuteBlocklyCommand
from px4_msgs.msg import VehicleStatus, VehicleLocalPosition, VehicleLandDetected
rclpy.init(); n = Node('release_check'); st = {}
n.create_subscription(VehicleStatus, '/fmu/out/vehicle_status_v1', lambda m: st.__setitem__('arm', m.arming_state), qos_profile_sensor_data)
n.create_subscription(VehicleLocalPosition, '/fmu/out/vehicle_local_position', lambda m: st.update(x=m.x, y=m.y, z=m.z, yaw=m.heading), qos_profile_sensor_data)
n.create_subscription(VehicleLandDetected, '/fmu/out/vehicle_land_detected', lambda m: st.__setitem__('landed', m.landed), qos_profile_sensor_data)
cli = n.create_client(ExecuteBlocklyCommand, '/dexi/execute_blockly_command'); assert cli.wait_for_service(15.0), 'manager service missing'
def spin(s):
    t0 = time.time()
    while time.time() - t0 < s: rclpy.spin_once(n, timeout_sec=0.1)
def call(command, parameter=0.0, timeout=30.0, **kw):
    r = ExecuteBlocklyCommand.Request(command=command, parameter=float(parameter), timeout=float(timeout))
    for k, v in kw.items(): setattr(r, k, float(v))
    f = cli.call_async(r)
    while rclpy.ok() and not f.done(): rclpy.spin_once(n, timeout_sec=0.1)
    res = f.result(); print(f'  {command:24s} -> {res.success} {res.message}', flush=True); return res.success
def until(pred, s):
    t0 = time.time()
    while time.time() - t0 < s:
        spin(0.3)
        if pred(): return True
    return False
fails = 0
spin(3); print('1. arm on the ground, wait, disarm', flush=True)
call('start_offboard_heartbeat'); call('arm'); ok = until(lambda: st.get('arm') == 2, 8); spin(5)
call('disarm'); ok = ok and until(lambda: st.get('arm') == 1, 6)
print('PASS ground disarm' if ok else 'FAIL ground disarm', flush=True); fails += not ok; spin(2)
print('2. takeoff, hold_ned, land, takeoff again', flush=True)
call('start_offboard_heartbeat'); call('arm'); until(lambda: st.get('arm') == 2, 8); spin(1.5)
z0 = st.get('z', 0.0); ok = call('offboard_takeoff', 1.0) and (z0 - st['z']) > 0.6
call('hold_ned', north=st['x'], east=st['y'], down=st['z'], yaw=st['yaw'] * 57.2958); spin(3)
call('land'); ok = ok and until(lambda: st.get('arm') == 1 and st.get('landed'), 60); spin(3)
call('start_offboard_heartbeat'); call('arm'); until(lambda: st.get('arm') == 2, 8); spin(1.5)
z0 = st.get('z', 0.0); ok2 = call('offboard_takeoff', 1.0) and (z0 - st['z']) > 0.6
call('land'); until(lambda: st.get('arm') == 1 and st.get('landed'), 60)
print('PASS takeoff after a hold_ned mission' if ok and ok2 else 'FAIL takeoff after a hold_ned mission', flush=True); fails += not (ok and ok2)
raise SystemExit(1 if fails else 0)
