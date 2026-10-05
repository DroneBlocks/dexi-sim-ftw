// One viewer page per check: it is the drone camera (headless render at the publish rate)
// and, through its ROSLIB, our connection to rosbridge. Nothing here needs ROS on the host.
import { chromium } from 'playwright';

export const HOST = process.env.HOST || '127.0.0.1';
export const SCENE = process.env.SCENE || 'lab';
export const sleep = (ms) => new Promise(r => setTimeout(r, ms));

export async function openSim({ scene = SCENE, camera = true } = {}) {
  const browser = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
  const page = await browser.newPage({ viewport: { width: 640, height: 480 } });
  const url = `http://${HOST}:1337/viewer-corridor.html?autoconnect=1&scene=${scene}&ws=ws%3A%2F%2F${HOST}%3A9090`
    + (camera ? '&headless=1&rate=5' : '&rate=1');
  await page.goto(url, { waitUntil: 'load' });
  await page.waitForFunction(() => window._sim && window._sim.connected, null, { timeout: 60000 });
  const state = () => page.evaluate(() => ({ ...window._sim.state }));
  const tags = () => page.evaluate(() => window._sim.tags.map(t => ({ ...t })));
  const svc = (service, type, req, timeoutMs = 60000) => page.evaluate(([service, type, req, timeoutMs]) => new Promise((res, rej) => {
    const ros = new ROSLIB.Ros({ url: document.getElementById('ws-url').value });
    const t = setTimeout(() => { ros.close(); rej(new Error('service timeout ' + service)); }, timeoutMs);
    ros.on('connection', () => {
      new ROSLIB.Service({ ros, name: service, serviceType: type }).callService(new ROSLIB.ServiceRequest(req),
        r => { clearTimeout(t); ros.close(); res(r); }, e => { clearTimeout(t); ros.close(); rej(new Error(String(e))); });
    });
  }), [service, type, req, timeoutMs]);
  const cmd = (command, parameter = 0, extra = {}, timeout = 60) =>
    svc('/dexi/execute_blockly_command', 'dexi_interfaces/srv/ExecuteBlocklyCommand', { command, parameter, timeout, ...extra }, (timeout + 5) * 1000);
  const once = (topic, type, timeoutMs = 10000) => page.evaluate(([topic, type, timeoutMs]) => new Promise((res, rej) => {
    const ros = new ROSLIB.Ros({ url: document.getElementById('ws-url').value });
    const t = setTimeout(() => { ros.close(); rej(new Error('no message on ' + topic)); }, timeoutMs);
    ros.on('connection', () => { const s = new ROSLIB.Topic({ ros, name: topic, messageType: type }); s.subscribe(m => { clearTimeout(t); s.unsubscribe(); ros.close(); res(m); }); });
  }), [topic, type, timeoutMs]);
  const waitFor = async (fn, ms, label = '') => { const t0 = Date.now(); while (Date.now() - t0 < ms) { if (fn(await state())) return true; await sleep(250); } throw new Error(`timeout waiting for ${label || fn}`); };
  return { browser, page, state, tags, svc, cmd, once, waitFor, close: () => browser.close() };
}

export function result(name, ok, detail = '') { console.log(`${ok ? 'PASS' : 'FAIL'} ${name}${detail ? ' — ' + detail : ''}`); if (!ok) process.exitCode = 1; }
