// A demo mission from the GCS menu, flown through the real GCS page: the XML is loaded into
// tab 1 the way the GCS stores it, Launch is clicked, and the GCS's own console verdict counts.
import { chromium } from 'playwright';
import { readFileSync, existsSync } from 'node:fs';
import { HOST, openSim, result, sleep } from '../lib/ros.mjs';
const DEMO = process.argv[2] || 'Takeoff and Land';
const candidates = [process.env.DEMOS, `${process.env.HOME}/_dev/dexi-droneblocks/assets/ts/demos.ts`, `${process.env.HOME}/_dev/dexi-droneblocks-apriltag/assets/ts/demos.ts`].filter(Boolean);
// First demos.ts that holds this demo wins (an older checkout may lack it).
const re = new RegExp(`name:\\s*'${DEMO.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}'[\\s\\S]*?blocklyXml:\\s*\`([\\s\\S]*?)\``);
let xml = null, demosPath = null;
for (const f of candidates.filter(existsSync)) { const m = readFileSync(f, 'utf8').match(re); if (m) { xml = m[1]; demosPath = f; break; } }
if (!xml) { result(`blockly ${DEMO}`, false, `demo not found in ${candidates.filter(existsSync).join(', ') || 'any demos.ts (set DEMOS)'}`); process.exit(1); }
const sim = await openSim({ camera: true });                      // camera + PX4 state
const browser = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
const gcs = await browser.newPage({ viewport: { width: 1400, height: 900 } });
await gcs.addInitScript(({ xml }) => {
  localStorage.setItem('droneblocks_mission_1', xml);
  localStorage.setItem('droneblocks_tabs', JSON.stringify([{ id: 1, name: 'Check', workspace: null }]));
  localStorage.setItem('droneblocks_active_tab', '1'); localStorage.setItem('droneblocks_next_tab_id', '2');
  localStorage.setItem('droneblocks_view_mode', 'simulator');
  localStorage.setItem('droneblocks_tutorial_progress', JSON.stringify({ completedLessons: [], lessonsStarted: {}, lessonsCompleted: {}, skippedTutorial: true }));
}, { xml });
let verdict = null; const log = [];
gcs.on('console', msg => { const t = msg.text(); if (/Mission completed successfully/.test(t)) verdict = 'ok'; if (/Mission failed/.test(t)) verdict = t; if (/✅|❌|🚁|Executing/.test(t)) log.push(t); });
try {
  await gcs.goto(`http://${HOST}/droneblocks`, { waitUntil: 'load' });
  const launch = gcs.locator('button', { hasText: 'Launch' }); await launch.waitFor({ timeout: 60000 });
  await gcs.waitForFunction(() => { const b = [...document.querySelectorAll('button')].find(x => x.textContent.includes('Launch')); return b && !b.disabled; }, null, { timeout: 60000 });
  await sleep(3000);
  const blocks = await gcs.evaluate(() => document.querySelectorAll('.blocklyDraggable').length);
  await sim.waitFor(s => s.valid, 60000, 'PX4 position valid');
  const t0 = Date.now(); await launch.click();
  const deadline = +(process.env.MISSION_SECONDS || 180) * 1000;
  while (!verdict && Date.now() - t0 < deadline) await sleep(500);
  // The land block returns once the aircraft is low; PX4 finishes the landing and disarms
  // on its own a few seconds later. Give it that time before judging.
  let st = await sim.state(); const t1 = Date.now();
  while (st.armed && Date.now() - t1 < 45000) { await sleep(500); st = await sim.state(); }
  const ok = verdict === 'ok' && !st.armed;
  result(`blockly "${DEMO}"`, ok, `${blocks} blocks, ${((Date.now() - t0) / 1000).toFixed(0)} s, verdict ${verdict || 'none'}, armed ${st.armed}`);
  if (!ok) console.log(log.slice(-8).join('\n'));
} finally { await browser.close(); await sim.close(); }
