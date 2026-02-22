import re
from .base import LLMBackend, InferenceResult

# Patterns: (compiled_regex, command_name, response_template)
# {v} is replaced with the matched value in the response template.
_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    # Offboard lifecycle
    (re.compile(r"\b(?:start|begin|enable)\b.*\bheartbeat\b", re.I),
     "start_offboard_heartbeat", "Starting offboard heartbeat."),
    (re.compile(r"\b(?:stop|end|disable)\b.*\bheartbeat\b", re.I),
     "stop_offboard_heartbeat", "Stopping offboard heartbeat."),

    # Arm / disarm
    (re.compile(r"\barm\b(?!.*\bdisarm\b)", re.I),
     "arm", "Arming the drone."),
    (re.compile(r"\bdisarm\b", re.I),
     "disarm", "Disarming the drone."),

    # Takeoff — extract optional altitude
    (re.compile(
        r"\b(?:take\s*off|takeoff|launch|lift\s*off)\b"
        r"(?:.*?(\d+(?:\.\d+)?)\s*(?:m(?:eters?)?|ft)?)?",
        re.I),
     "offboard_takeoff", "Taking off to {v} meters."),

    # Land
    (re.compile(r"\bland\b", re.I),
     "land", "Landing."),

    # Directional flight — extract distance
    (re.compile(
        r"\bfly\s+forward\b(?:.*?(\d+(?:\.\d+)?)\s*(?:m(?:eters?)?)?)?", re.I),
     "fly_forward", "Flying forward {v} meters."),
    (re.compile(
        r"\bfly\s+back(?:ward)?s?\b(?:.*?(\d+(?:\.\d+)?)\s*(?:m(?:eters?)?)?)?", re.I),
     "fly_backward", "Flying backward {v} meters."),
    (re.compile(
        r"\bfly\s+left\b(?:.*?(\d+(?:\.\d+)?)\s*(?:m(?:eters?)?)?)?", re.I),
     "fly_left", "Flying left {v} meters."),
    (re.compile(
        r"\bfly\s+right\b(?:.*?(\d+(?:\.\d+)?)\s*(?:m(?:eters?)?)?)?", re.I),
     "fly_right", "Flying right {v} meters."),
    (re.compile(
        r"\bfly\s+up\b(?:.*?(\d+(?:\.\d+)?)\s*(?:m(?:eters?)?)?)?", re.I),
     "fly_up", "Flying up {v} meters."),
    (re.compile(
        r"\bfly\s+down\b(?:.*?(\d+(?:\.\d+)?)\s*(?:m(?:eters?)?)?)?", re.I),
     "fly_down", "Flying down {v} meters."),

    # Yaw — extract degrees
    (re.compile(
        r"\b(?:yaw|turn|rotate)\s+left\b"
        r"(?:.*?(\d+(?:\.\d+)?)\s*(?:deg(?:rees?)?|°)?)?", re.I),
     "yaw_left", "Yawing left {v} degrees."),
    (re.compile(
        r"\b(?:yaw|turn|rotate)\s+right\b"
        r"(?:.*?(\d+(?:\.\d+)?)\s*(?:deg(?:rees?)?|°)?)?", re.I),
     "yaw_right", "Yawing right {v} degrees."),
]

# Default values when no number is extracted
_DEFAULTS = {
    "offboard_takeoff": 1.5,
    "fly_forward": 1.0,
    "fly_backward": 1.0,
    "fly_left": 1.0,
    "fly_right": 1.0,
    "fly_up": 0.5,
    "fly_down": 0.5,
    "yaw_left": 90.0,
    "yaw_right": 90.0,
}


class KeywordBackend(LLMBackend):
    def infer(self, prompt: str, node=None) -> InferenceResult:
        for pattern, command, response_tpl in _PATTERNS:
            m = pattern.search(prompt)
            if m:
                # Extract numeric value from first capture group if present
                raw = m.group(1) if m.lastindex and m.lastindex >= 1 else None
                value = float(raw) if raw else _DEFAULTS.get(command, 0.0)
                response = response_tpl.replace("{v}", f"{value:g}")
                return InferenceResult(
                    command=command,
                    value=value,
                    response=response,
                )

        return InferenceResult(
            command="",
            value=0.0,
            response=f"Sorry, I didn't understand: \"{prompt}\"",
            success=False,
        )
