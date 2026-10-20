"""Dynamics fingerprint of PX4 flights, for matching the sim to real DEXI-3 logs.

Per log (airborne segments only):
  hover_thrust      median hover_thrust_estimate (valid samples)
  rate_lag_ms       lag that maximises the cross-correlation of roll/pitch rate setpoint vs measured rate (rate-loop delay)
  rate_gain         regression slope measured/setpoint at that lag (tracking amplitude)
  drag_k            tilt [rad] per (m/s) of steady horizontal speed: tan(tilt) = k * v  (linear drag / (m g))
  acc_p95           95th percentile horizontal acceleration [m/s^2]
Usage: python dyn_metrics.py <log.ulg>... [--json out.json]
"""
import json
import sys

import numpy as np
from pyulog import ULog

TOPICS = ["vehicle_land_detected", "vehicle_local_position", "hover_thrust_estimate", "vehicle_rates_setpoint",
          "vehicle_angular_velocity", "vehicle_attitude"]


def ds(u, n):
    try:
        return u.get_dataset(n).data
    except Exception:          # noqa: BLE001
        return None


def interp(t, src_t, v):
    return np.interp(t, src_t, v)


def metrics(path):
    u = ULog(path, TOPICS)
    ld = ds(u, "vehicle_land_detected")
    if ld is None:
        return None
    lt = ld["timestamp"] / 1e6
    air = ~ld["landed"].astype(bool)

    def airborne(t):
        idx = np.searchsorted(lt, t, side="right") - 1
        return air[np.clip(idx, 0, len(air) - 1)]
    out = {"file": path}
    h = ds(u, "hover_thrust_estimate")
    if h is not None:
        ok = h["valid"].astype(bool) if "valid" in h else np.ones(len(h["timestamp"]), bool)
        out["hover_thrust"] = float(np.median(h["hover_thrust"][ok])) if ok.any() else None
    sp, av = ds(u, "vehicle_rates_setpoint"), ds(u, "vehicle_angular_velocity")
    if sp is not None and av is not None:
        t = np.arange(max(sp["timestamp"][0], av["timestamp"][0]), min(sp["timestamp"][-1], av["timestamp"][-1]), 2000) / 1e6
        m = airborne(t)
        lags, gains = [], []
        for ax, (ks, ka) in enumerate((("roll", "xyz[0]"), ("pitch", "xyz[1]"))):
            s = interp(t, sp["timestamp"] / 1e6, sp[ks])[m]
            a = interp(t, av["timestamp"] / 1e6, av[ka])[m]
            if len(s) < 2000 or np.std(s) < 0.05:
                continue
            s, a = s - s.mean(), a - a.mean()
            k = 50                                   # 0.1 s moving average -> keep > ~2 Hz content (pilot vs autopilot excitation differ below that)
            s = s - np.convolve(s, np.ones(k) / k, "same")
            a = a - np.convolve(a, np.ones(k) / k, "same")
            best = max(range(0, 60), key=lambda L: np.dot(s[:len(s) - L], a[L:]))
            lags.append(best * 2.0)
            gains.append(float(np.dot(s[:len(s) - best], a[best:]) / np.dot(s[:len(s) - best], s[:len(s) - best])))
        if lags:
            out["rate_lag_ms"], out["rate_gain"] = float(np.mean(lags)), float(np.mean(gains))
    lp, att = ds(u, "vehicle_local_position"), ds(u, "vehicle_attitude")
    if lp is not None and att is not None:
        t = lp["timestamp"] / 1e6
        m = airborne(t)
        vx, vy = lp["vx"], lp["vy"]
        ax_, ay_ = lp["ax"], lp["ay"]
        q = np.stack([interp(t, att["timestamp"] / 1e6, att[f"q[{i}]"]) for i in range(4)], 1)
        w, x, y, z = q.T
        tilt = np.arccos(np.clip(1 - 2 * (x * x + y * y), -1, 1))
        v = np.hypot(vx, vy)
        acc = np.hypot(ax_, ay_)
        steady = m & (acc < 0.3) & (v > 0.3)
        if steady.sum() > 50:
            out["drag_k"] = float(np.sum(np.tan(tilt[steady]) * v[steady]) / np.sum(v[steady] ** 2))
            out["steady_n"] = int(steady.sum())
        if m.any():
            out["acc_p95"] = float(np.percentile(acc[m], 95))
            out["v_max"] = float(np.max(v[m]))
    out["air_s"] = float(np.sum(np.diff(lt)[air[:-1]]))
    return out


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    res = []
    for f in args:
        try:
            r = metrics(f)
        except Exception as e:  # noqa: BLE001
            r = {"file": f, "error": str(e)}
        if r:
            res.append(r)
            print(json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}))
    if "--json" in sys.argv:
        json.dump(res, open(sys.argv[sys.argv.index("--json") + 1], "w"), indent=1)
