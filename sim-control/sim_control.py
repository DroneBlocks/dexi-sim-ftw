#!/usr/bin/env python3
"""Tiny HTTP control surface for the SITL stack, so a dashboard button can reset the
simulation without anyone touching Docker.

    POST /reset            -> aircraft back on tag 0 (Gazebo teleport; PX4's estimator follows in ~12 s)
    POST /reset?n=0&e=3.0  -> at a NED position in meters
    GET  /health

Runs next to px4-sitl with GAZEBO_MASTER_URI pointing at it. It refuses when the
model is off the ground; callers (the court page, the dashboard) also refuse while
PX4 is armed. A teleport under a flying estimator is a crash.
"""
import json
import math
import os
import subprocess
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

MODEL = os.environ.get('SIM_MODEL', 'iris')


def gz(*args):
    return subprocess.run(['gz', 'model', '-m', MODEL, *args], capture_output=True, text=True, timeout=15)


def model_pose():
    """(height, yaw) of the model from `gz model -i`, or (None, None) if Gazebo is unreachable."""
    out = gz('-i').stdout
    try:
        pos = out.split('position {', 1)[1]
        z = float(pos.split('z:', 1)[1].split()[0])
    except (IndexError, ValueError):
        return None, None
    yaw = 0.0
    if 'orientation {' in out:
        try:
            o = out.split('orientation {', 1)[1].split('}', 1)[0]
            q = {k: float(o.split(k + ':', 1)[1].split()[0]) for k in ('x', 'y', 'z', 'w')}
            yaw = math.atan2(2 * (q['w'] * q['z'] + q['x'] * q['y']), 1 - 2 * (q['y'] ** 2 + q['z'] ** 2))
        except (IndexError, ValueError, KeyError):
            pass
    return z, yaw


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self._send(204, {})

    def do_GET(self):
        if urlparse(self.path).path == '/health':
            h, yaw = model_pose()
            return self._send(200, {'ok': True, 'model': MODEL, 'height': h, 'yaw': yaw})
        self._send(404, {'error': 'use POST /reset'})

    def do_POST(self):
        url = urlparse(self.path)
        if url.path != '/reset':
            return self._send(404, {'error': 'use POST /reset'})
        q = parse_qs(url.query)
        north = float(q.get('n', ['0'])[0])
        east = float(q.get('e', ['0'])[0])
        h, yaw = model_pose()
        if h is None:
            return self._send(503, {'error': 'Gazebo not reachable'})
        if h > 0.2:
            return self._send(409, {'error': f'aircraft is airborne ({h:.2f} m); land and disarm first'})
        # Gazebo is ENU (x east, y north); PX4 reports NED. Keep the model's yaw: a yaw jump
        # under a running estimator reads as a magnetometer fault and PX4 refuses to arm.
        r = gz('-x', str(east), '-y', str(north), '-z', '0.12', '-R', '0', '-P', '0', '-Y', str(yaw))
        if r.returncode != 0:
            return self._send(500, {'error': r.stderr.strip()[:200]})
        self._send(200, {'ok': True, 'north': north, 'east': east, 'note': 'estimator settles in about 12 s'})

    def log_message(self, fmt, *args):
        print(time.strftime('%H:%M:%S'), fmt % args, flush=True)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8090'))
    print(f'sim-control on :{port}, model {MODEL}, GAZEBO_MASTER_URI={os.environ.get("GAZEBO_MASTER_URI")}', flush=True)
    HTTPServer(('0.0.0.0', port), Handler).serve_forever()
