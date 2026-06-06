from app.core.ai_providers.base_provider import BaseAIProvider, ProviderCapabilities
from app.schemas.ai_engine import AIEngineTestResult


class QwenAdapter(BaseAIProvider):
    """
    Qwen / DashScope API adapter.

    DashScope OpenAI-compatible endpoint:
    - base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
    - Uses /v1 prefix with the OpenAI SDK.
    - /models endpoint may not be fully supported; we primarily test via chat completions.
    """
    provider_name = "qwen"
    capabilities = ProviderCapabilities(
        supports_models_list=False,
        requires_v1_prefix=True,
        auth_header_name="Authorization",
        auth_header_value_prefix="Bearer ",
    )

    aliases = {"dashscope", "aliyun", "tongyi", "qwen"}

    async def test_connection(
        self, api_base: str, api_key: str, model: str, proxy_url: str = ""
    ) -> AIEngineTestResult:
        headers = self.get_auth_headers(api_key)
        api_base = self.normalize_api_base(api_base)

        result = await self._try_chat_endpoint(api_base, headers, model, proxy_url=proxy_url)
        if result.success:
            return result

        return result
