# DEXI-3 body: where each number comes from and how it was checked

The DEXI-3 variant (`docker-compose.dexi3.yml`) flies `px4-gazebo-slim/models/dexi3/dexi3.sdf`. This page lists every physical
number in it, its source, and the check that was run. **All checks are in simulation**. A value labelled LOG-FITTED was
matched to real DEXI-3 flight logs; nothing here was measured on a scale, a pendulum or a thrust stand.

| Quantity | Value | Label | Source / method |
|---|---|---|---|
| Total mass | 0.432 kg | ASSUMED | dexi-roadmap Dev Kit figure; no DEXI-3 has been weighed (Flight Kit figure 381 g) |
| Motor square | 110 × 110 mm (±0.055 m) | SOURCE | Dev Kit CAD |
| Prop radius | 0.0381 m | SOURCE | Gemfan 3018 (3 in) |
| Max thrust (all four) | 700 g (motorConstant 1.4188e-06 at 1100 rad/s) | INFERRED | 432 g ÷ the Dev Kit's logged hover thrust 0.613–0.662 (KB fact 299). Inherits the mass assumption; no thrust data exists |
| Inertia | ixx 7.78e-4, iyy 1.02e-3, izz 1.44e-3 kg·m² | INFERRED | component box breakdown of the Dev Kit, scaled to 0.432 kg. **Not fitted** (see below) |
| Rotor drag | 4.8e-05 | LOG-FITTED | tilt-per-speed, below |
| Motor time constants | 0.0125 / 0.025 s | iris values, kept | the rate-loop lag already matches the logs, below |
| Moment constant (yaw) | 0.012 | ASSUMED | small-prop torque/thrust ratio; the airframe's CA_ROTOR*_KM matches it |

## Method: dynamics fingerprints
`scripts/dexi3_fit/dyn_metrics.py <log.ulg>...` computes the same numbers from a real log or a sim log:
- `drag_k`: tan(tilt) = k · v in steady horizontal flight (|accel| < 0.3 m/s², v > 0.3 m/s);
- `rate_lag_ms` / `rate_gain`: roll/pitch rate setpoint vs measured rate;
- `hover_thrust`.

Real targets come from 40 real DEXI-3 logs (39 usable). The logs are the DEXI-3 flights in `DroneBlocks/dexi-log-analysis` (`logs/board-*`) plus one
BNSF flight. They are not in this repo; ask the DEXI team for access.

| Fingerprint | Real DEXI-3 median (IQR, n) | Sim, iris drag (before) | Sim, fitted drag (after) |
|---|---|---|---|
| drag_k [rad per m/s] | 0.045 (0.040–0.079, n = 15) | 0.153 | **0.046** |
| rate_lag_ms | 46 (44–52.5, n = 39) | 48 | 50 |
| rate_gain | 0.69 (0.47–0.85, n = 39) | 0.48 | 0.47 |
| hover thrust | 0.47 (0.46–0.50, n = 39), see note | 0.571 | 0.585 |

Sim flights: `fly_forward 10` / `fly_backward 10` at 1.5 m on the F1 body with the DEXI-3 tune. The rotor drag was solved from the
plugin's drag model (drag = |w| · c · v per rotor, so k = 4 · w_hover · c / (m g)) and then corrected once from the measured
0.052 → 4.8e-05.

## Limits, stated plainly
- **Not a hold-out validation.** With 15 usable logs and a 5× spread (0.024–0.116), the target is the 15-log median. The
  fitted value is inside the IQR of the alternating half of the logs (0.040–0.069) but that half was not held out of the target.
- **Inertia is not fitted.** The rate gain sits at the lower edge of the real IQR. Lower inertia or a different moment
  constant could move it, and so could the tune. Measuring the inertia (bifilar pendulum) is the right next step before fitting.
- **Hover thrust is not comparable 1:1.** The real fleet runs THR_MDL_FAC 0.3 on its own ESCs and an unknown mass. The sim body
  uses THR_MDL_FAC 1.0 (its thrust curve), so 0.585 vs 0.47 says nothing about the mass by itself.
- No ground effect, no turbulence, no prop wash (DexiSim has no hook for extra forces).
