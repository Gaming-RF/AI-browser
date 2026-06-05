"""
OpenAI Agent Implementation

Implements the BaseAIAgent interface for OpenAI's models.
Supports custom base URLs for local model servers (Ollama, LM Studio, vLLM).
"""

import os
from typing import Optional
import base64
from src.agents.base_agent import BaseAIAgent

try:
    from openai import AsyncOpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


class OpenAIAgent(BaseAIAgent):
    """AI Agent using OpenAI's API (or any OpenAI-compatible endpoint)."""

    def __init__(
        self,
        model: str = "gpt-4",
        api_key: Optional[str] = None,
        api_base_url: Optional[str] = None,
    ):
        """Initialize OpenAI agent.

        Args:
            model: Model name (e.g. "gpt-4", "llama3", "mistral").
            api_key: API key.  Optional when using a local server.
            api_base_url: Custom endpoint (e.g. http://localhost:11434/v1).
        """
        super().__init__(model, api_key, api_base_url)

        if not HAS_OPENAI:
            raise ImportError(
                "openai package not installed. Install with: pip install openai"
            )

        # Resolve API key — local servers usually don't need a real key
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key and not api_base_url:
            raise ValueError(
                "OPENAI_API_KEY not found.  Set it in your environment, "
                ".env file, or config.yaml.  If you are using a local model, "
                "set api_base_url instead."
            )

        # Build client kwargs
        client_kwargs = {"api_key": self.api_key or "local-model"}
        if api_base_url:
            client_kwargs["base_url"] = api_base_url

        self.client = AsyncOpenAI(**client_kwargs)

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
                {"type": "text", "text": message},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"},
                },
            ]
        else:
            user_content = message

        self.add_to_history("user", user_content)

        # ── Assemble messages list ─────────────────────────
        messages = [{"role": "system", "content": self.system_prompt}]
        for m in self.conversation_history:
            messages.append({"role": m.role, "content": m.content})

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=2000,
        )

        assistant_message = response.choices[0].message.content
        self.add_to_history("assistant", assistant_message)
        return assistant_message

    async def vision_analyze(self, image_data: bytes, prompt: str) -> str:
        """Analyze an image using OpenAI's vision capabilities."""
        base64_image = base64.b64encode(image_data).decode("utf-8")

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
            max_tokens=1024,
        )

        return response.choices[0].message.content
