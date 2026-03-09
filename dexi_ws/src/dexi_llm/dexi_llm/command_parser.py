from dexi_interfaces.msg import OffboardNavCommand
from .backends.base import InferenceResult

# Commands that use the NED fields
_NED_COMMANDS = {"goto_ned"}


def to_nav_command(result: InferenceResult) -> OffboardNavCommand:
    """Convert an InferenceResult into an OffboardNavCommand message."""
    msg = OffboardNavCommand()
    msg.command = result.command
    msg.distance_or_degrees = result.value

    if result.command in _NED_COMMANDS:
        msg.north = result.north
        msg.east = result.east
        msg.down = result.down
        msg.yaw = result.yaw

    return msg
