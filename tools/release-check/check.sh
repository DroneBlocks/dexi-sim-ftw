#!/bin/bash
# Functional checks against a running DEXI sim stack. Usage: HOST=<ip> ./check.sh [check ...]
# Docker commands go to the stack's daemon (set DOCKER_HOST=ssh://root@<ip> for a remote stack).
# Each flight check starts from a fresh PX4 (aircraft at the origin over tag 0, full battery).
set -u
cd "$(dirname "$0")"
export HOST=${HOST:-127.0.0.1}
mkdir -p logs; : > logs/summary.txt
if [ ! -d node_modules ]; then npm install --silent --no-audit --no-fund && npx playwright install chromium >/dev/null 2>&1; fi
svc() { docker ps -q --filter "label=com.docker.compose.service=$1" | head -1; }
reset_px4() {
  echo "-- reset PX4 (aircraft back to the origin, fresh battery)"
  docker restart "$(svc px4-sitl)" "$(svc micro-dds-agent)" >/dev/null && sleep 35
}
run() { local name=$1; shift; echo "== $name"; local t0=$SECONDS
  if "$@" > "logs/$name.log" 2>&1; then echo "PASS $name ($((SECONDS - t0)) s)" | tee -a logs/summary.txt
  else echo "FAIL $name ($((SECONDS - t0)) s): logs/$name.log" | tee -a logs/summary.txt; grep -E "PASS|FAIL|Error|error" "logs/$name.log" | tail -6; fi; }
WANT=${*:-"stack blockly-takeoff-land blockly-square nodered-flow python-offboard color yolo mavsdk regressions"}
want() { [[ " $WANT " == *" $1 "* ]]; }
want stack              && run stack node checks/stack.mjs
want blockly-takeoff-land && { reset_px4; run blockly-takeoff-land node checks/blockly.mjs "Takeoff and Land"; }
want blockly-square     && { reset_px4; run blockly-square node checks/blockly.mjs "Square Pattern"; }
want nodered-flow       && { reset_px4; run nodered-flow node checks/nodered-flow.mjs; }
if want python-offboard || want color || want yolo || want mavsdk || want regressions; then
  node lib/publisher.mjs > logs/publisher.log 2>&1 & PUB=$!; sleep 15
  want python-offboard && { reset_px4; run python-offboard bash checks/python-offboard.sh; }
  want color           && { reset_px4; run color bash checks/color.sh; }
  want yolo            && { reset_px4; run yolo bash checks/yolo.sh; }
  want mavsdk          && { reset_px4; run mavsdk bash checks/mavsdk.sh; }
  want regressions     && { reset_px4; run regressions bash checks/regressions.sh; }
  kill $PUB 2>/dev/null
fi
echo; echo "== summary (HOST=$HOST)"; cat logs/summary.txt
grep -q "^FAIL" logs/summary.txt && exit 1 || exit 0
