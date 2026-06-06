from app.core.ai_providers.base_provider import BaseAIProvider, ProviderCapabilities
from app.schemas.ai_engine import AIEngineTestResult


class DeepSeekAdapter(BaseAIProvider):
    """
    DeepSeek API adapter.

    Per official docs (https://api-docs.deepseek.com/):
    - OpenAI-compatible base_url: https://api.deepseek.com
    - Chat completions: POST https://api.deepseek.com/chat/completions
    - The API does NOT use a /v1 prefix with the OpenAI SDK.
    - The /models endpoint is NOT publicly documented; we use chat completions for testing.
    """
    provider_name = "deepseek"
    capabilities = ProviderCapabilities(
        supports_models_list=False,
        requires_v1_prefix=False,
        auth_header_name="Authorization",
        auth_header_value_prefix="Bearer ",
    )

    async def test_connection(
        self, api_base: str, api_key: str, model: str, proxy_url: str = ""
    ) -> AIEngineTestResult:
        headers = self.get_auth_headers(api_key)
        api_base = self.normalize_api_base(api_base)

        result = await self._try_chat_endpoint(api_base, headers, model, proxy_url=proxy_url)
        if result.success:
            return result

        return result
