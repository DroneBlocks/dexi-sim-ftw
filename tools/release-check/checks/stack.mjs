// Every service answers; PX4, the camera and the detector reach rosbridge clients.
import { HOST, openSim, result, sleep } from '../lib/ros.mjs';
const http = async (url) => { try { const r = await fetch(url, { redirect: 'manual' }); return r.status; } catch { return 0; } };
for (const [name, url, ok] of [['GCS', `http://${HOST}/droneblocks`, [200]], ['simulator', `http://${HOST}:1337/viewer-corridor.html`, [200]],
  ['environments manifest', `http://${HOST}:1337/environments.json`, [200]], ['Node-RED', `http://${HOST}:1880/`, [200, 301, 302]],
  ['code-server', `http://${HOST}:9999/`, [200, 302]], ['mavlink2rest', `http://${HOST}:8088/`, [200]]]) {
  const s = await http(url); result(`http ${name}`, ok.includes(s), `${url} -> ${s}`);
}
const sim = await openSim({ camera: true });
try {
  const st = await sim.once('/fmu/out/vehicle_status_v1', 'px4_msgs/msg/VehicleStatus', 15000).catch(() => null);
  result('PX4 vehicle_status via rosbridge', !!st, st ? `arming_state ${st.arming_state} nav_state ${st.nav_state}` : 'nothing in 15 s');
  const pos = await sim.once('/fmu/out/vehicle_local_position', 'px4_msgs/msg/VehicleLocalPosition', 10000).catch(() => null);
  result('PX4 local position via rosbridge', !!pos, pos ? `z ${pos.z.toFixed(2)}` : 'nothing in 10 s');
  const cam = await sim.once('/cam0/image_raw/compressed', 'sensor_msgs/msg/CompressedImage', 10000).catch(() => null);
  result('camera frames on /cam0', !!cam, cam ? `${cam.format}, ${Math.round(cam.data.length * 0.75 / 1024)} kB` : 'nothing in 10 s');
  const det = await sim.once('/apriltag_detections', 'apriltag_msgs/msg/AprilTagDetectionArray', 10000).catch(() => null);
  result('AprilTag detector publishing', !!det, det ? `${det.detections.length} tags in view on the ground` : 'nothing in 10 s');
  const tn = await sim.once('/dexi/tag_nav/status', 'std_msgs/msg/String', 10000).catch(() => null);
  result('tag_nav status', !!tn, tn ? JSON.parse(tn.data).state : 'nothing in 10 s');
  const mg = await sim.once('/dexi/offboard_manager/status', 'std_msgs/msg/String', 10000).catch(() => null);
  result('offboard manager status', !!mg, mg ? JSON.parse(mg.data).control_mode : 'nothing in 10 s');
} finally { await sim.close(); }
