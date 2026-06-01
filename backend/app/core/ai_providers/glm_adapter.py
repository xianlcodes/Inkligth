from app.core.ai_providers.base_provider import BaseAIProvider, ProviderCapabilities
from app.schemas.ai_engine import AIEngineTestResult


class GLMAdapter(BaseAIProvider):
    """
    GLM / ZhipuAI API adapter.

    ZhipuAI OpenAI-compatible endpoint:
    - base_url: https://open.bigmodel.cn/api/paas/v4
    - Models: glm-4.7-flash, glm-4.7, glm-4.6, etc.
    - Does NOT use /v1 prefix with the OpenAI SDK.
    - glm-4.7-flash is free-tier and recommended for translation.
    """
    provider_name = "glm"
    capabilities = ProviderCapabilities(
        supports_models_list=True,
        requires_v1_prefix=False,
        auth_header_name="Authorization",
        auth_header_value_prefix="Bearer ",
    )

    aliases = {"zhipu", "zhipuai", "chatglm"}

    async def test_connection(
        self, api_base: str, api_key: str, model: str
    ) -> AIEngineTestResult:
        headers = self.get_auth_headers(api_key)
        api_base = self.normalize_api_base(api_base)

        result = await self._try_models_endpoint(api_base, headers)
        if result and result.success:
            return result

        return await self._try_chat_endpoint(api_base, headers, model)
