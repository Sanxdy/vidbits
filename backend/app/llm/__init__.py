from app.config import settings
from app.llm.base import LLMProvider
from app.llm.ollama_provider import OllamaProvider
from app.llm.openai_provider import OpenAIProvider


def get_llm_provider() -> LLMProvider:
    if settings.llm_provider == "ollama":
        return OllamaProvider()
    return OpenAIProvider()


__all__ = ["LLMProvider", "get_llm_provider"]
