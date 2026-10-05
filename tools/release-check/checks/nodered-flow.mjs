// The Node-RED tag-navigation flow runs the mission; this script is the pilot. Verdict: the
// aircraft lands and disarms within 0.5 m of the last tag of the flow's route.
import { HOST, openSim, result, sleep } from '../lib/ros.mjs';
const NR = `http://${HOST}:1880`;
const flows = await (await fetch(`${NR}/flows`)).json();
const tab = flows.find(n => n.type === 'tab' && n.id === 'tagnav_tab');
if (!tab) { result('node-red flow', false, 'DEXI Tag Navigation flow is not deployed (tab tagnav_tab)'); process.exit(1); }
const mission = flows.find(n => n.type === 'function' && /const ROUTE\s*=/.test(n.func || ''));
const route = JSON.parse(mission.func.match(/const ROUTE\s*=\s*(\[[^\]]*\])/)[1]);
const inject = (id) => fetch(`${NR}/inject/tagnav_${id}`, { method: 'POST' }).then(r => r.status);
const sim = await openSim({ camera: true });
try {
  const tags = await sim.tags(); const last = tags.find(t => t.id === route[route.length - 1]);
  if (!last) throw new Error(`route ends on tag ${route[route.length - 1]}, not in this environment`);
  await sim.waitFor(s => s.valid, 60000, 'PX4 position valid');
  if ((await inject('inj_arm')) !== 200) throw new Error('inject inj_arm failed'); await sleep(1500);
  if ((await inject('inj_pilot')) !== 200) throw new Error('inject inj_pilot failed');
  await sim.waitFor(s => -s.d > 1.0, 40000, 'pilot takeoff');
  await sleep(2000);
  if ((await inject('inj_engage')) !== 200) throw new Error('inject inj_engage failed');
  const t0 = Date.now(); let s;
  while (Date.now() - t0 < 300000) { s = await sim.state(); if (!s.armed && Date.now() - t0 > 10000) break; await sleep(500); }
  const dist = Math.hypot(s.n - last.north, s.e - last.east);
  result(`node-red flow route ${JSON.stringify(route)}`, !s.armed && dist < 0.5, `ended ${dist.toFixed(2)} m from tag ${last.id} after ${((Date.now() - t0) / 1000).toFixed(0)} s, armed ${s.armed}`);
} catch (e) { result('node-red flow', false, e.message); } finally { await sim.close(); }
