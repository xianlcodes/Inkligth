import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

import httpx

from app.schemas.ai_engine import AIEngineTestResult

logger = logging.getLogger(__name__)

DEFAULT_RETRY_COUNT = 2
DEFAULT_RETRY_DELAY = 1.0
DEFAULT_TIMEOUT = 30.0


@dataclass
class ProviderCapabilities:
    supports_models_list: bool = True
    requires_v1_prefix: bool = True
    auth_header_name: str = "Authorization"
    auth_header_value_prefix: str = "Bearer "
    content_type: str = "application/json"


class BaseAIProvider(ABC):
    provider_name: str = "generic"
    capabilities: ProviderCapabilities = ProviderCapabilities()

    def normalize_api_base(self, api_base: str) -> str:
        api_base = api_base.strip()
        if not api_base.startswith(('http://', 'https://')):
            api_base = 'https://' + api_base
        return api_base.rstrip('/')

    def get_auth_headers(self, api_key: str) -> dict:
        return {
            self.capabilities.auth_header_name:
                self.capabilities.auth_header_value_prefix + api_key,
            "Content-Type": self.capabilities.content_type,
        }

    def get_openai_base_url(self, api_base: str) -> str:
        """
        Returns the base URL suitable for the OpenAI SDK's `base_url` parameter.
        The OpenAI SDK appends paths like `/chat/completions` to this URL.
        """
        base = self.normalize_api_base(api_base)
        if self.capabilities.requires_v1_prefix and not base.endswith('/v1'):
            base = base + '/v1'
        return base

    def _build_url(self, api_base: str, path: str) -> str:
        base = self.normalize_api_base(api_base)
        path = path.lstrip('/')
        if self.capabilities.requires_v1_prefix and '/v1' not in base:
            return f"{base}/v1/{path}"
        return f"{base}/{path}"

    async def _try_models_endpoint(
        self, api_base: str, headers: dict
    ) -> Optional[AIEngineTestResult]:
        if not self.capabilities.supports_models_list:
            return None
        url = self._build_url(api_base, "models")
        last_error = None
        for attempt in range(DEFAULT_RETRY_COUNT + 1):
            try:
                async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                    response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    models = [m.get("id", m.get("name", "")) for m in data.get("data", [])]
                    return AIEngineTestResult(
                        success=True,
                        message="连接成功",
                        models=models,
                    )
                logger.info(
                    f"[{self.provider_name}] /models returned {response.status_code}, "
                    f"falling back to chat endpoint test"
                )
                return None
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_error = e
                if attempt < DEFAULT_RETRY_COUNT:
                    logger.warning(
                        f"[{self.provider_name}] /models attempt {attempt + 1} failed: {e}, retrying..."
                    )
                    await asyncio.sleep(DEFAULT_RETRY_DELAY * (attempt + 1))
            except Exception as e:
                logger.warning(f"[{self.provider_name}] /models endpoint failed: {e}")
                return None
        logger.error(f"[{self.provider_name}] /models all retries exhausted: {last_error}")
        return None

    async def _try_chat_endpoint(
        self, api_base: str, headers: dict, model: str
    ) -> AIEngineTestResult:
        test_payload = {
            "model": model,
            "max_tokens": 1,
            "messages": [{"role": "user", "content": "hi"}],
        }
        url = self._build_url(api_base, "chat/completions")
        last_result = None

        for attempt in range(DEFAULT_RETRY_COUNT + 1):
            try:
                async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                    response = await client.post(url, json=test_payload, headers=headers)
                status = response.status_code

                if status == 200:
                    return AIEngineTestResult(
                        success=True,
                        message="连接成功",
                        models=[model],
                    )
                if status == 400:
                    return AIEngineTestResult(
                        success=True,
                        message="连接成功（鉴权验证通过，模型参数可能需要调整）",
                        models=[],
                    )
                if status in (401, 403):
                    return AIEngineTestResult(
                        success=False,
                        message=self._diagnose_auth_error(status, response),
                        models=[],
                    )
                if status in (301, 302, 303, 307, 308):
                    return AIEngineTestResult(
                        success=False,
                        message=self._diagnose_redirect_error(status, response, url),
                        models=[],
                    )
                if status == 429:
                    if attempt < DEFAULT_RETRY_COUNT:
                        retry_after = response.headers.get("Retry-After", str(DEFAULT_RETRY_DELAY * (attempt + 1)))
                        logger.warning(
                            f"[{self.provider_name}] rate limited (429), "
                            f"retrying after {retry_after}s"
                        )
                        await asyncio.sleep(float(retry_after))
                        continue
                    return AIEngineTestResult(
                        success=False,
                        message=f"[{self.provider_name.upper()}] 请求频率过高 (429)，请稍后重试",
                        models=[],
                    )
                if status >= 500 and attempt < DEFAULT_RETRY_COUNT:
                    logger.warning(
                        f"[{self.provider_name}] server error ({status}), "
                        f"attempt {attempt + 1}, retrying..."
                    )
                    await asyncio.sleep(DEFAULT_RETRY_DELAY * (attempt + 1))
                    continue
                last_result = AIEngineTestResult(
                    success=False,
                    message=self._diagnose_generic_error(status, response, url),
                    models=[],
                )
                return last_result

            except httpx.TimeoutException:
                if attempt < DEFAULT_RETRY_COUNT:
                    logger.warning(
                        f"[{self.provider_name}] timeout attempt {attempt + 1}, retrying..."
                    )
                    await asyncio.sleep(DEFAULT_RETRY_DELAY * (attempt + 1))
                    continue
                return AIEngineTestResult(
                    success=False,
                    message="连接超时：API 服务器未在 30 秒内响应，请检查网络连接或 API 地址是否正确",
                    models=[],
                )
            except httpx.ConnectError:
                return AIEngineTestResult(
                    success=False,
                    message=f"无法连接到服务器：{self.normalize_api_base(api_base)}，请检查 API 地址和网络连接",
                    models=[],
                )
            except Exception as e:
                logger.error(f"[{self.provider_name}] chat endpoint test failed: {e}")
                return AIEngineTestResult(
                    success=False,
                    message=f"连接异常: {str(e)}",
                    models=[],
                )

        return last_result or AIEngineTestResult(
            success=False,
            message=f"[{self.provider_name.upper()}] 重试 {DEFAULT_RETRY_COUNT} 次后仍然失败",
            models=[],
        )

    @abstractmethod
    async def test_connection(
        self, api_base: str, api_key: str, model: str
    ) -> AIEngineTestResult:
        ...

    def _diagnose_auth_error(self, status: int, response) -> str:
        try:
            body = response.json()
            detail = body.get("error", {}).get("message", "")
        except Exception:
            detail = ""
        provider = self.provider_name.upper()
        if status == 401:
            base_msg = f"[{provider}] 认证失败 (401)：API Key 无效或已过期"
        else:
            base_msg = f"[{provider}] 权限不足 (403)：API Key 没有访问该模型的权限"
        if detail:
            base_msg += f" — {detail}"
        base_msg += "。请检查 API Key 是否正确，以及是否有该模型的访问权限。"
        return base_msg

    def _diagnose_redirect_error(self, status: int, response, url: str) -> str:
        location = response.headers.get("Location", "未知")
        provider = self.provider_name.upper()
        return (
            f"[{provider}] 请求被重定向 ({status}) → {location}。"
            f"请求的 URL 为: {url}。"
            f"请确认 API 地址是否正确。对于 {self.provider_name}，"
            f"正确的 API 地址应为相应的官方地址。"
        )

    def _diagnose_generic_error(self, status: int, response, url: str) -> str:
        try:
            body = response.json()
            detail = body.get("error", {}).get("message", str(body)[:200])
        except Exception:
            detail = response.text[:200] if response.text else "无详细信息"
        provider = self.provider_name.upper()
        return (
            f"[{provider}] 请求失败，HTTP {status}。"
            f"请求 URL: {url}。响应: {detail}"
        )
