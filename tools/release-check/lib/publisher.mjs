// Keep one camera page open for the checks that run inside the containers (Python, MAVSDK).
import { openSim, sleep } from './ros.mjs';
const sim = await openSim({ camera: true });
console.log('camera publisher up');
await sleep(+(process.env.PUBLISH_SECONDS || 1800) * 1000);
await sim.close();
