
from app.llm import get_llm_provider
from app.llm.base import LLMProvider
from app.llm.ollama_provider import OllamaProvider
from app.llm.openai_provider import OpenAIProvider


def test_openai_provider_type():
    provider = OpenAIProvider()
    assert isinstance(provider, LLMProvider)


def test_ollama_provider_type():
    provider = OllamaProvider()
    assert isinstance(provider, LLMProvider)


def test_provider_switch_openai(monkeypatch):
    monkeypatch.setattr("app.config.settings.llm_provider", "openai")
    provider = get_llm_provider()
    assert isinstance(provider, OpenAIProvider)


def test_provider_switch_ollama(monkeypatch):
    monkeypatch.setattr("app.config.settings.llm_provider", "ollama")
    provider = get_llm_provider()
    assert isinstance(provider, OllamaProvider)
