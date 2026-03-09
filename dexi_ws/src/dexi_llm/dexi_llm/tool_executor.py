"""Agentic tool-calling loop for fine-tuned models with llama-cpp-python.

Builds chat prompts using model-specific templates from config/models.json,
parses <tool_call> tags from the model output, executes tools via RosTools,
and feeds results back as <tool_response> messages.
"""

import json
import re
import time
from dataclasses import dataclass, field

from rclpy.node import Node

from .ros_tools import RosTools, TOOL_DEFINITIONS
from .config import load_system_prompt, load_model_config, build_system_block

MAX_ITERATIONS = 3
MAX_TOOL_RESULT_CHARS = 500

# Regex to extract tool calls: <tool_call>{"name": "...", "arguments": {...}}</tool_call>
_TOOL_CALL_RE = re.compile(
    r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL
)


@dataclass
class ToolCallRecord:
    """Record of a single tool call + result."""
    name: str
    arguments: dict
    result: str


@dataclass
class AgenticResult:
    """Result from a complete agentic loop."""
    response: str = ""
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    iterations: int = 0
    total_inference_ms: int = 0


class ToolExecutor:
    """Runs the agentic inference loop."""

    def __init__(self, model, node: Node, model_name: str = "qwen2.5-1.5b"):
        """
        Args:
            model: A llama_cpp.Llama instance.
            node: The ROS 2 node (for tool execution).
            model_name: Key into models.json for chat template / stop tokens.
        """
        self._model = model
        self._node = node
        self._tools = RosTools(node)
        self._logger = node.get_logger()

        # Load model-specific config
        config = load_model_config(model_name)
        self._tpl = config["chat_template"]
        self._stop_tokens = config["stop_tokens"]

        # Pre-build the system block (model-agnostic content)
        system_prompt = load_system_prompt()
        self._system_block = build_system_block(system_prompt, TOOL_DEFINITIONS)

    def run(self, user_prompt: str) -> AgenticResult:
        """Execute the agentic loop and return the final result."""
        result = AgenticResult()
        failed_services = set()
        completed_subscriptions = set()  # topics already read

        # Build initial prompt with model-specific chat template
        prompt = self._build_initial_prompt(user_prompt)

        for iteration in range(MAX_ITERATIONS):
            result.iterations = iteration + 1

            # Run inference
            t0 = time.monotonic()
            output_text = self._generate(prompt)
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            result.total_inference_ms += elapsed_ms

            self._logger.info(
                f"Iteration {iteration + 1}: "
                f"generated {len(output_text)} chars in {elapsed_ms}ms"
            )

            # Parse tool calls
            tool_calls = self._parse_tool_calls(output_text)

            if not tool_calls:
                # No tool calls — this is the final text response
                result.response = output_text.strip()
                return result

            # Execute each tool call and collect results
            tool_results = []
            action_succeeded = False
            action_failed_permanently = False

            for tc_name, tc_args in tool_calls:
                # Skip topics we already subscribed to
                if tc_name == "subscribe_once":
                    topic = tc_args.get("topic", "")
                    if topic in completed_subscriptions:
                        self._logger.info(
                            f"Skipping duplicate subscribe: {topic}")
                        continue
                # Skip services we already know are unavailable
                if tc_name == "call_service":
                    svc = tc_args.get("service", "")
                    if svc in failed_services:
                        self._logger.info(
                            f"Skipping already-failed service: {svc}")
                        tool_result = json.dumps({
                            "error": f"Service {svc} is not available."
                        })
                        action_failed_permanently = True
                    else:
                        self._logger.info(
                            f"Tool call: {tc_name}({json.dumps(tc_args)})")
                        tool_result = self._tools.execute(tc_name, tc_args)

                        # Track failed services
                        if "not available" in tool_result or "timed out" in tool_result.lower():
                            failed_services.add(svc)
                            action_failed_permanently = True
                        elif '"success": true' in tool_result or '"success":true' in tool_result:
                            action_succeeded = True
                else:
                    self._logger.info(
                        f"Tool call: {tc_name}({json.dumps(tc_args)})")
                    tool_result = self._tools.execute(tc_name, tc_args)
                    # Track successful subscriptions
                    if tc_name == "subscribe_once" and "error" not in tool_result.lower():
                        completed_subscriptions.add(tc_args.get("topic", ""))

                # Truncate long results
                if len(tool_result) > MAX_TOOL_RESULT_CHARS:
                    tool_result = tool_result[:MAX_TOOL_RESULT_CHARS] + "\n... (truncated)"

                record = ToolCallRecord(
                    name=tc_name, arguments=tc_args, result=tool_result
                )
                result.tool_calls.append(record)
                tool_results.append((tc_name, tc_args, tool_result))

                self._logger.info(
                    f"Tool result ({tc_name}): {tool_result[:200]}"
                )

            # For single-tool, single-intent calls: if the tool succeeded,
            # stop the loop and use the assistant's text as the response.
            text_before_tool = output_text[:output_text.find("<tool_call>")].strip()
            all_succeeded = all(
                '"success": true' in r or '"success":true' in r
                for _, _, r in tool_results
            )
            if len(tool_calls) == 1 and text_before_tool and all_succeeded:
                result.response = text_before_tool
                return result

            # For multi-tool calls where at least one action succeeded
            if action_succeeded:
                result.response = text_before_tool or "Done!"
                return result

            # If the service is permanently unavailable, report and stop
            if action_failed_permanently and not any(
                tc_name != "call_service" for tc_name, _ in tool_calls
            ):
                result.response = (
                    "Sorry, that service isn't available right now."
                )
                return result

            # Append the assistant output + tool results to the prompt
            prompt += output_text
            # Close the assistant turn if needed
            if not output_text.rstrip().endswith(self._tpl["assistant_suffix"].strip()):
                prompt += self._tpl["assistant_suffix"]

            # Add tool results as a user message
            tool_response_parts = []
            for tc_name, tc_args, tc_result in tool_results:
                tool_response_parts.append(
                    f"<tool_response>\n{tc_result}\n</tool_response>"
                )

            prompt += (
                self._tpl["user_prefix"]
                + "\n".join(tool_response_parts)
                + self._tpl["user_suffix"]
                + self._tpl["assistant_prefix"]
            )

        # If we exhausted iterations, return whatever we have
        result.response = (
            "I completed the available tool calls but ran out of iterations."
        )
        return result

    def _build_initial_prompt(self, user_prompt: str) -> str:
        """Build the initial prompt with model-specific chat template."""
        tpl = self._tpl
        return (
            tpl["bos"]
            + tpl["system_prefix"] + self._system_block + tpl["system_suffix"]
            + tpl["user_prefix"] + user_prompt + tpl["user_suffix"]
            + tpl["assistant_prefix"]
        )

    def _generate(self, prompt: str) -> str:
        """Run a single llama.cpp completion."""
        output = self._model(
            prompt,
            max_tokens=256,
            temperature=0.1,
            stop=self._stop_tokens,
        )
        return output["choices"][0]["text"]

    def _parse_tool_calls(self, text: str) -> list[tuple[str, dict]]:
        """Extract tool calls from model output.

        Returns a list of (tool_name, arguments) tuples.
        """
        calls = []
        for match in _TOOL_CALL_RE.finditer(text):
            try:
                data = json.loads(match.group(1))
                name = data.get("name", "")
                arguments = data.get("arguments", {})
                if name:
                    calls.append((name, arguments))
            except json.JSONDecodeError:
                self._logger.warn(f"Failed to parse tool call JSON: {match.group(1)}")
        return calls
