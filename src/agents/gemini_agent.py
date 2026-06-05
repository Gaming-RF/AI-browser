"""
Google Gemini Agent Implementation

Implements the BaseAIAgent interface for Google's Gemini models.
"""

import os
from typing import Optional
import base64
from src.agents.base_agent import BaseAIAgent

try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


class GeminiAgent(BaseAIAgent):
    """AI Agent using Google's Gemini API."""

    def __init__(
        self,
        model: str = "gemini-2.0-flash",
        api_key: Optional[str] = None,
        api_base_url: Optional[str] = None,
    ):
        """Initialize Gemini agent.

        Args:
            model: Model name (e.g. "gemini-2.0-flash", "gemini-1.5-pro").
            api_key: Google API key.
            api_base_url: Not used for Gemini (kept for interface compat).
        """
        super().__init__(model, api_key, api_base_url)

        if not HAS_GENAI:
            raise ImportError(
                "google-genai package not installed. "
                "Install with: pip install google-genai"
            )

        self.api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GOOGLE_API_KEY or GEMINI_API_KEY not found. "
                "Set it in your environment, .env file, or config.yaml."
            )

        self.client = genai.Client(api_key=self.api_key)

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
        parts = [message]

        if image_data:
            parts.append(types.Part.from_bytes(
                data=image_data,
                mime_type="image/png",
            ))

        self.add_to_history("user", message)

        # ── Assemble messages list ─────────────────────────
        contents = []
        for m in self.conversation_history:
            contents.append(types.Content(
                role=m.role if m.role != "assistant" else "model",
                parts=[types.Part.from_text(text=m.content if isinstance(m.content, str) else str(m.content))],
            ))

        # Replace the last user message with the multimodal one if we have image
        if image_data and contents:
            contents[-1] = types.Content(
                role="user",
                parts=parts,
            )

        config = types.GenerateContentConfig(
            system_instruction=self.system_prompt,
            temperature=0.7,
            max_output_tokens=2000,
        )

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        )

        assistant_message = response.text
        self.add_to_history("assistant", assistant_message)
        return assistant_message

    async def vision_analyze(self, image_data: bytes, prompt: str) -> str:
        """Analyze an image using Gemini's vision capabilities."""

        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=prompt),
                    types.Part.from_bytes(data=image_data, mime_type="image/png"),
                ],
            )
        ]

        config = types.GenerateContentConfig(
            max_output_tokens=1024,
        )

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        )

        return response.text
