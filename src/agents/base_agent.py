"""
Base Agent Interface

Defines the abstract interface for AI agents.
Implementations can use OpenAI, Anthropic, local models, or any other provider.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class Message:
    """Represents a message in the conversation."""
    role: str  # "user" or "assistant"
    content: Any  # str for text-only, list for multimodal


class BaseAIAgent(ABC):
    """Abstract base class for AI agents."""

    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        api_base_url: Optional[str] = None,
    ):
        """
        Initialize the AI agent.

        Args:
            model: Model identifier (e.g., "gpt-4", "claude-3-opus", "llama3")
            api_key: API key for the service (if None, reads from environment)
            api_base_url: Custom API endpoint for local / self-hosted models
        """
        self.model = model
        self.api_key = api_key
        self.api_base_url = api_base_url
        self.conversation_history: List[Message] = []

    @abstractmethod
    async def send_message(
        self,
        message: str,
        image_data: Optional[bytes] = None,
    ) -> str:
        """
        Send a message to the AI and get a response.

        Args:
            message: The user message (text prompt)
            image_data: Optional screenshot bytes for vision-capable models

        Returns:
            The AI's response as a string
        """
        pass

    @abstractmethod
    async def vision_analyze(self, image_data: bytes, prompt: str) -> str:
        """
        Analyze an image with the AI.

        Args:
            image_data: The image bytes
            prompt: The analysis prompt

        Returns:
            The analysis result
        """
        pass

    def add_to_history(self, role: str, content: Any):
        """Add a message to conversation history."""
        self.conversation_history.append(Message(role=role, content=content))

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []

    def get_history(self) -> List[Message]:
        """Get conversation history."""
        return self.conversation_history
