"""AI Collaboration Tool - Agile-style PM + Developer AI teamwork"""

from .ai_clients import AIClient, OpenAIClient, AnthropicClient, create_client, Message
from .workflow import CollaborationWorkflow, WorkflowResult, WorkflowPhase, TaskType

__version__ = "1.0.0"
__all__ = [
    "AIClient",
    "OpenAIClient",
    "AnthropicClient",
    "create_client",
    "Message",
    "CollaborationWorkflow",
    "WorkflowResult",
    "WorkflowPhase",
    "TaskType",
]
