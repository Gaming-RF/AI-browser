"""
Anthropic Agent Implementation

Implements the BaseAIAgent interface for Anthropic's Claude models.
"""

import os
from typing import Optional
import base64
from src.agents.base_agent import BaseAIAgent

try:
    from anthropic import AsyncAnthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


class AnthropicAgent(BaseAIAgent):
    """AI Agent using Anthropic's Claude API."""

    def __init__(
        self,
        model: str = "claude-3-opus-20240229",
        api_key: Optional[str] = None,
        api_base_url: Optional[str] = None,
    ):
        """Initialize Anthropic agent."""
        super().__init__(model, api_key, api_base_url)

        if not HAS_ANTHROPIC:
            raise ImportError(
                "anthropic package not installed. Install with: pip install anthropic"
            )

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not found in environment variables"
            )

        client_kwargs = {"api_key": self.api_key}
        if api_base_url:
            client_kwargs["base_url"] = api_base_url

        self.client = AsyncAnthropic(**client_kwargs)

        self.system_prompt = (
            "You are an intelligent browser automation agent. "
            "You have the ability to control a web browser and perform tasks. "
            "You should analyze the current state of the browser and decide "
            "what actions to take.  Always think step-by-step about what "
            "needs to be done."
        )

    async def send_message(
        self,
        message: str,
        image_data: Optional[bytes] = None,
    ) -> str:
        """Send a message (optionally with a screenshot) and get a response."""

        # ── Build user content ─────────────────────────────
        if image_data:
            b64 = base64.b64encode(image_data).decode("utf-8")
            user_content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": b64,
                    },
                },
                {"type": "text", "text": message},
            ]
        else:
            user_content = message

        self.add_to_history("user", user_content)

        # ── Assemble messages list ─────────────────────────
        messages = []
        for m in self.conversation_history:
            messages.append({"role": m.role, "content": m.content})

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            system=self.system_prompt,
            messages=messages,
        )

        assistant_message = response.content[0].text
        self.add_to_history("assistant", assistant_message)
        return assistant_message

    async def vision_analyze(self, image_data: bytes, prompt: str) -> str:
        """Analyze an image using Claude's vision capabilities."""
        base64_image = base64.b64encode(image_data).decode("utf-8")

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": base64_image,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )

        return response.content[0].text
