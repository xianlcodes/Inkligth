from app.core.ai_providers.base_provider import BaseAIProvider, ProviderCapabilities
from app.schemas.ai_engine import AIEngineTestResult


class OpenAIAdapter(BaseAIProvider):
    provider_name = "openai"
    capabilities = ProviderCapabilities(
        supports_models_list=True,
        requires_v1_prefix=True,
        auth_header_name="Authorization",
        auth_header_value_prefix="Bearer ",
    )

    async def test_connection(
        self, api_base: str, api_key: str, model: str
    ) -> AIEngineTestResult:
        headers = self.get_auth_headers(api_key)
        api_base = self.normalize_api_base(api_base)

        result = await self._try_models_endpoint(api_base, headers)
        if result and result.success:
            return result

        return await self._try_chat_endpoint(api_base, headers, model)
