from .base import LLMBackend, InferenceResult, ToolCallRecord
from .keyword_backend import KeywordBackend


class LlamaBackend(LLMBackend):
    def __init__(self, model_path: str, n_ctx: int = 2048, n_threads: int = 4,
                 model_name: str = "qwen2.5-1.5b"):
        try:
            from llama_cpp import Llama
        except ImportError:
            raise ImportError(
                "llama-cpp-python is required for the llama_cpp backend. "
                "Install with: pip install llama-cpp-python"
            )

        self._model = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_threads=n_threads,
            verbose=False,
        )
        self._model_name = model_name
        self._fallback = KeywordBackend()
        self._tool_executor = None

    def infer(self, prompt: str, node=None) -> InferenceResult:
        # Lazy-init the ToolExecutor once we have a node handle
        if node is not None and self._tool_executor is None:
            from ..tool_executor import ToolExecutor
            self._tool_executor = ToolExecutor(
                self._model, node, model_name=self._model_name
            )

        # If we have a tool executor, run the agentic loop
        if self._tool_executor is not None:
            try:
                return self._run_agentic(prompt)
            except Exception as exc:
                # Log and fall back to keyword
                if node is not None:
                    node.get_logger().error(
                        f"Agentic loop failed, falling back to keyword: {exc}"
                    )
                return self._fallback.infer(prompt)

        # No node available — fall back to keyword
        return self._fallback.infer(prompt)

    def _run_agentic(self, prompt: str) -> InferenceResult:
        """Run the agentic tool-calling loop and map to InferenceResult."""
        agentic = self._tool_executor.run(prompt)

        # Extract commands from call_service tool calls
        commands_executed = []
        for tc in agentic.tool_calls:
            if tc.name == "call_service":
                cmd = tc.arguments.get("args", {}).get("command", "")
                if cmd:
                    commands_executed.append(cmd)

        # Map ToolCallRecords
        tool_records = [
            ToolCallRecord(name=tc.name, arguments=tc.arguments, result=tc.result)
            for tc in agentic.tool_calls
        ]

        return InferenceResult(
            response=agentic.response,
            success=True,
            tool_calls=tool_records,
            iterations=agentic.iterations,
            inference_ms=agentic.total_inference_ms,
            commands_executed=commands_executed,
        )
