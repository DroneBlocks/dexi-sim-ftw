from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ToolCallRecord:
    """Record of a single tool call and its result."""
    name: str = ""
    arguments: dict = field(default_factory=dict)
    result: str = ""


@dataclass
class InferenceResult:
    command: str = ""
    value: float = 0.0
    response: str = ""
    # NED fields for goto_ned
    north: float = 0.0
    east: float = 0.0
    down: float = 0.0
    yaw: float = 0.0
    success: bool = True
    # Agentic fields
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    iterations: int = 0
    inference_ms: int = 0
    commands_executed: list[str] = field(default_factory=list)


class LLMBackend(ABC):
    @abstractmethod
    def infer(self, prompt: str, node=None) -> InferenceResult:
        """Process a natural language prompt and return a parsed command."""
        ...
