// The Node-RED Tag Navigation tab runs the TAG HOP mission; this script presses the button.
// Verdict: the aircraft lands and disarms within 0.5 m of the tag the mission lands on.
import { HOST, openSim, result, sleep } from '../lib/ros.mjs';
const NR = `http://${HOST}:1880`;
const flows = await (await fetch(`${NR}/flows`)).json();
const tab = flows.find(n => n.type === 'tab' && n.id === 'tagnav_tab');
if (!tab) { result('node-red flow', false, 'DEXI Tag Navigation flow is not deployed (tab tagnav_tab)'); process.exit(1); }
const byId = Object.fromEntries(flows.map(n => [n.id, n]));
const start = flows.find(n => n.z === 'tagnav_tab' && n.type === 'inject' && n.name === 'TAG HOP');
if (!start) { result('node-red flow', false, 'no TAG HOP inject on the Tag Navigation tab'); process.exit(1); }
// Follow the chain from the button to its last node, which lands on the target tag.
const route = []; let node = start;
while (node.wires?.[0]?.length) { node = byId[node.wires[0][0]]; if (node.tag !== undefined) route.push(Number(node.tag)); }
if (node.type !== 'dexi-tag-land') { result('node-red flow', false, `TAG HOP ends on ${node.type}, not dexi-tag-land`); process.exit(1); }
// Every tab ships disabled; enable this one for the run and put it back afterward.
const setTab = async (disabled) => {
  const flow = await (await fetch(`${NR}/flow/tagnav_tab`)).json();
  const r = await fetch(`${NR}/flow/tagnav_tab`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...flow, disabled }) });
  if (r.status !== 200) throw new Error(`could not set tagnav_tab disabled=${disabled} (${r.status})`);
};
const wasDisabled = !!tab.disabled;
const sim = await openSim({ camera: true });
try {
  if (wasDisabled) { await setTab(false); await sleep(2000); }
  const tags = await sim.tags(); const last = tags.find(t => t.id === route[route.length - 1]);
  if (!last) throw new Error(`route ends on tag ${route[route.length - 1]}, not in this environment`);
  await sim.waitFor(s => s.valid, 60000, 'PX4 position valid');
  const status = await fetch(`${NR}/inject/${start.id}`, { method: 'POST' }).then(r => r.status);
  if (status !== 200) throw new Error(`inject TAG HOP failed (${status})`);
  await sim.waitFor(s => s.armed, 20000, 'armed by the flow');
  const t0 = Date.now(); let s;
  while (Date.now() - t0 < 300000) { s = await sim.state(); if (!s.armed && Date.now() - t0 > 10000) break; await sleep(500); }
  const dist = Math.hypot(s.n - last.north, s.e - last.east);
  result(`node-red flow route ${JSON.stringify(route)}`, !s.armed && dist < 0.5, `ended ${dist.toFixed(2)} m from tag ${last.id} after ${((Date.now() - t0) / 1000).toFixed(0)} s, armed ${s.armed}`);
} catch (e) { result('node-red flow', false, e.message); } finally {
  if (wasDisabled) await setTab(true).catch(e => console.log(e.message));
  await sim.close();
}
