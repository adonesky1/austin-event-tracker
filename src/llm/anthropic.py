import json

import anthropic
import structlog

from src.llm.base import LLMClient

logger = structlog.get_logger()


class AnthropicLLMClient(LLMClient):
    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001"):
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model

    async def complete(self, prompt: str, system: str | None = None) -> str:
        kwargs: dict = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        response = await self._client.messages.create(**kwargs)
        return response.content[0].text

    async def complete_json(self, prompt: str, system: str | None = None) -> dict:
        json_system = (system or "") + "\n\nRespond ONLY with valid JSON. No explanation, no markdown."
        text = await self.complete(prompt, system=json_system.strip())
        try:
            # Strip markdown code fences if present
            cleaned = text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error("llm_json_parse_error", error=str(e), text=text[:200])
            raise
