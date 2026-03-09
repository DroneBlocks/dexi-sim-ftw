#!/usr/bin/env python3

import rclpy
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from std_msgs.msg import String
from dexi_interfaces.msg import OffboardNavCommand
from dexi_interfaces.srv import LLMChat

from .backends.base import LLMBackend
from .command_parser import to_nav_command


class LLMNode(Node):
    def __init__(self):
        super().__init__('llm_node')

        # Parameters
        self.declare_parameter('backend', 'keyword')
        self.declare_parameter('model_path', '')
        self.declare_parameter('model_name', 'qwen2.5-1.5b')
        self.declare_parameter('n_ctx', 2048)
        self.declare_parameter('n_threads', 4)

        backend_name = self.get_parameter('backend').value
        model_path = self.get_parameter('model_path').value
        model_name = self.get_parameter('model_name').value
        n_ctx = self.get_parameter('n_ctx').value
        n_threads = self.get_parameter('n_threads').value

        # Initialize backend
        self._backend = self._create_backend(
            backend_name, model_path, n_ctx, n_threads, model_name
        )

        # Publisher: text response
        self._response_pub = self.create_publisher(
            String, '/dexi/llm/response', 10)

        # Publisher: offboard commands (match existing offboard manager QoS)
        offboard_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )
        self._cmd_pub = self.create_publisher(
            OffboardNavCommand, '/dexi/offboard_manager', offboard_qos)

        # Subscriber: prompt input
        self._prompt_sub = self.create_subscription(
            String, '/dexi/llm/prompt', self._on_prompt, 10)

        # Reentrant callback group so the agentic loop can create
        # transient service clients inside this service callback
        # without deadlocking the executor.
        self._reentrant_group = ReentrantCallbackGroup()

        # Service: synchronous chat
        self._chat_srv = self.create_service(
            LLMChat, '~/chat', self._on_chat,
            callback_group=self._reentrant_group)

        self.get_logger().info(
            f'LLM node ready (backend={backend_name}, model={model_name})')

    def _create_backend(
        self, name: str, model_path: str, n_ctx: int, n_threads: int,
        model_name: str = "qwen2.5-1.5b",
    ) -> LLMBackend:
        if name == 'keyword':
            from .backends.keyword_backend import KeywordBackend
            return KeywordBackend()
        elif name == 'llama_cpp':
            if not model_path:
                self.get_logger().error(
                    'model_path is required for llama_cpp backend')
                raise ValueError('model_path is required for llama_cpp backend')
            from .backends.llama_backend import LlamaBackend
            self.get_logger().info(f'Loading model: {model_path}')
            return LlamaBackend(
                model_path, n_ctx=n_ctx, n_threads=n_threads,
                model_name=model_name,
            )
        else:
            self.get_logger().error(f'Unknown backend: {name}')
            raise ValueError(f'Unknown backend: {name}')

    def _process_prompt(self, prompt: str) -> tuple[str, list[str]]:
        """Run inference and publish results. Returns (response_text, [commands])."""
        result = self._backend.infer(prompt, node=self)

        # Publish text response
        resp_msg = String()
        resp_msg.data = result.response
        self._response_pub.publish(resp_msg)

        # Agentic path: tool_calls were made (even if no drone commands)
        if result.tool_calls:
            commands_executed = list(result.commands_executed)
            tools_used = [tc.name for tc in result.tool_calls]
            self.get_logger().info(
                f'"{prompt}" -> agentic: tools={tools_used} '
                f'commands={commands_executed} '
                f'({result.iterations} iters, {result.inference_ms}ms)')
            return result.response, commands_executed

        # Keyword/legacy path: commands come from the single command field
        commands_executed: list[str] = []
        if result.success and result.command:
            nav_msg = to_nav_command(result)
            self._cmd_pub.publish(nav_msg)
            commands_executed.append(result.command)
            self.get_logger().info(
                f'"{prompt}" -> {result.command}({result.value:g})')
        else:
            self.get_logger().warn(f'No command parsed from: "{prompt}"')

        return result.response, commands_executed

    def _on_prompt(self, msg: String):
        self._process_prompt(msg.data)

    def _on_chat(self, request: LLMChat.Request, response: LLMChat.Response):
        resp_text, cmds = self._process_prompt(request.prompt)
        response.response = resp_text
        response.commands_executed = cmds
        # Success if we got commands OR a non-empty response
        response.success = len(cmds) > 0 or bool(resp_text)
        return response


def main(args=None):
    rclpy.init(args=args)
    node = LLMNode()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    try:
        executor.spin()
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        try:
            rclpy.shutdown()
        except Exception:
            pass


if __name__ == '__main__':
    main()
