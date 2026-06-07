import httpx

from app.config import settings
from app.llm.base import LLMProvider


class OllamaProvider(LLMProvider):
    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = "llama3"

    async def generate(self, prompt: str, max_tokens: int = 256) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "options": {"num_predict": max_tokens, "temperature": 0.3},
                    "stream": False,
                },
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["response"].strip()
