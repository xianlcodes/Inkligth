import logging
from typing import Optional

from app.core.ai_providers.base_provider import BaseAIProvider

logger = logging.getLogger(__name__)


class AIProviderRegistry:
    _instance: Optional["AIProviderRegistry"] = None
    _providers: dict[str, BaseAIProvider] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._providers = {}
        return cls._instance

    def register(self, provider: BaseAIProvider):
        name = provider.provider_name.lower()
        self._providers[name] = provider
        aliases = getattr(provider, 'aliases', set())
        for alias in aliases:
            self._providers[alias.lower()] = provider
        logger.info(f"Registered AI provider adapter: {name}"
                    + (f" (aliases: {aliases})" if aliases else ""))

    def get(self, provider_name: str) -> Optional[BaseAIProvider]:
        return self._providers.get(provider_name.lower())

    def get_or_default(self, provider_name: str, default_provider_name: str = "openai") -> BaseAIProvider:
        adapter = self.get(provider_name)
        if adapter:
            return adapter
        adapter = self.get(default_provider_name)
        if adapter:
            return adapter
        return GenericAIProvider()

    def list_providers(self) -> list[str]:
        return list(self._providers.keys())

    @classmethod
    def bootstrap(cls):
        registry = cls()
        from app.core.ai_providers.openai_adapter import OpenAIAdapter
        from app.core.ai_providers.deepseek_adapter import DeepSeekAdapter
        from app.core.ai_providers.qwen_adapter import QwenAdapter
        from app.core.ai_providers.glm_adapter import GLMAdapter

        registry.register(OpenAIAdapter())
        registry.register(DeepSeekAdapter())
        registry.register(QwenAdapter())
        registry.register(GLMAdapter())
        logger.info(f"AI provider registry bootstrapped with {len(registry._providers)} providers")
        return registry


class GenericAIProvider(BaseAIProvider):
    provider_name = "generic"

    async def test_connection(
        self, api_base: str, api_key: str, model: str, proxy_url: str = ""
    ):
        from app.schemas.ai_engine import AIEngineTestResult
        headers = self.get_auth_headers(api_key)
        api_base = self.normalize_api_base(api_base)

        result = await self._try_models_endpoint(api_base, headers, proxy_url=proxy_url)
        if result and result.success:
            return result

        return await self._try_chat_endpoint(api_base, headers, model, proxy_url=proxy_url)
