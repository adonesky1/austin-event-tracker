from abc import ABC, abstractmethod


class LLMClient(ABC):
    @abstractmethod
    async def complete(self, prompt: str, system: str | None = None) -> str: ...

    @abstractmethod
    async def complete_json(self, prompt: str, system: str | None = None) -> dict: ...
