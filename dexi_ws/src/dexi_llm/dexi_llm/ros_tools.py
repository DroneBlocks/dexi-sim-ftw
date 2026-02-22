"""ROS 2 tool implementations for the agentic LLM loop.

Each tool executes directly via rclpy (no rosbridge needed) because
the LLM node *is* a ROS 2 process.
"""

import importlib
import json
import threading
import time
from typing import Any

from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

from .config import load_tools

# ---------------------------------------------------------------------------
# Tool definitions (sent to the model in the system prompt)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = load_tools()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _import_message_class(type_str: str):
    """Import a ROS 2 message/service class from a type string.

    Accepts formats like:
        'std_msgs/msg/String'
        'dexi_interfaces/srv/ExecuteBlocklyCommand'
    """
    parts = type_str.replace("/", ".").rsplit(".", 1)  # ['std_msgs.msg', 'String']
    module = importlib.import_module(parts[0])
    return getattr(module, parts[1])


def _fill_message(msg, data: dict):
    """Recursively set fields on a ROS 2 message from a dict."""
    for key, value in data.items():
        if not hasattr(msg, key):
            continue
        if isinstance(value, dict):
            _fill_message(getattr(msg, key), value)
        else:
            setattr(msg, key, type(getattr(msg, key))(value))


def _msg_to_dict(msg) -> Any:
    """Convert a ROS 2 message to a JSON-serialisable dict."""
    if hasattr(msg, "get_fields_and_field_types"):
        result = {}
        for field_name in msg.get_fields_and_field_types():
            value = getattr(msg, field_name)
            result[field_name] = _msg_to_dict(value)
        return result
    if isinstance(msg, (list, tuple)):
        return [_msg_to_dict(item) for item in msg]
    if isinstance(msg, bytes):
        return f"<bytes len={len(msg)}>"
    # Primitive
    return msg


# ---------------------------------------------------------------------------
# RosTools class
# ---------------------------------------------------------------------------


class RosTools:
    """Execute ROS 2 tool calls on behalf of the LLM."""

    def __init__(self, node: Node):
        self._node = node
        self._logger = node.get_logger()

    # ---- get_topics -------------------------------------------------------

    def get_topics(self, **_kwargs) -> str:
        topics = self._node.get_topic_names_and_types()

        dexi_topics = []
        other_topics = []
        for name, types in sorted(topics):
            entry = f"{name} [{', '.join(types)}]"
            if name.startswith("/dexi/"):
                dexi_topics.append(entry)
            else:
                other_topics.append(entry)

        lines = []
        if dexi_topics:
            lines.append("=== Dexi Topics ===")
            lines.extend(dexi_topics)
        if other_topics:
            lines.append("=== Other Topics ===")
            # Limit to avoid context overflow
            lines.extend(other_topics[:40])
            if len(other_topics) > 40:
                lines.append(f"... and {len(other_topics) - 40} more")

        return "\n".join(lines)

    # ---- subscribe_once ---------------------------------------------------

    def subscribe_once(self, topic: str = "", msg_type: str = "", **_kwargs) -> str:
        if not topic or not msg_type:
            return "Error: 'topic' and 'msg_type' are required."

        try:
            msg_class = _import_message_class(msg_type)
        except (ImportError, AttributeError) as exc:
            return f"Error importing {msg_type}: {exc}"

        received = threading.Event()
        result_holder: list = []

        # Use BEST_EFFORT QoS to match PX4 / sensor topics
        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )

        def _callback(msg):
            if not result_holder:
                result_holder.append(msg)
                received.set()

        sub = self._node.create_subscription(msg_class, topic, _callback, qos)
        try:
            if not received.wait(timeout=3.0):
                return f"Timeout: no message received on {topic} within 3 seconds."
            return json.dumps(_msg_to_dict(result_holder[0]), default=str)
        finally:
            self._node.destroy_subscription(sub)

    # ---- call_service -----------------------------------------------------

    def call_service(
        self, service: str = "", service_type: str = "", args: dict | None = None,
        **_kwargs,
    ) -> str:
        if not service or not service_type:
            return "Error: 'service' and 'service_type' are required."

        try:
            srv_class = _import_message_class(service_type)
        except (ImportError, AttributeError) as exc:
            return f"Error importing {service_type}: {exc}"

        client = self._node.create_client(srv_class, service)
        try:
            if not client.wait_for_service(timeout_sec=3.0):
                return f"Service {service} not available (timeout 3s)."

            request = srv_class.Request()
            if args:
                _fill_message(request, args)

            future = client.call_async(request)

            # Poll for result — do NOT use spin_until_future_complete
            # (that would deadlock inside a service callback with
            #  SingleThreadedExecutor; safe with MultiThreaded but
            #  polling is simpler and always works).
            deadline = time.time() + 30.0
            while not future.done() and time.time() < deadline:
                time.sleep(0.05)

            if not future.done():
                return f"Service call to {service} timed out (30s)."

            response = future.result()
            return json.dumps(_msg_to_dict(response), default=str)
        finally:
            self._node.destroy_client(client)

    # ---- publish_message --------------------------------------------------

    def publish_message(
        self, topic: str = "", msg_type: str = "", message: dict | None = None,
        **_kwargs,
    ) -> str:
        if not topic or not msg_type:
            return "Error: 'topic' and 'msg_type' are required."

        try:
            msg_class = _import_message_class(msg_type)
        except (ImportError, AttributeError) as exc:
            return f"Error importing {msg_type}: {exc}"

        msg = msg_class()
        if message:
            _fill_message(msg, message)

        pub = self._node.create_publisher(msg_class, topic, 10)
        try:
            # Small delay to let discovery happen
            time.sleep(0.1)
            pub.publish(msg)
            return f"Published to {topic}."
        finally:
            self._node.destroy_publisher(pub)

    # ---- dispatch ---------------------------------------------------------

    def execute(self, tool_name: str, arguments: dict) -> str:
        """Dispatch a tool call by name."""
        fn = getattr(self, tool_name, None)
        if fn is None:
            return f"Unknown tool: {tool_name}"
        try:
            return fn(**arguments)
        except Exception as exc:
            return f"Tool error ({tool_name}): {exc}"
