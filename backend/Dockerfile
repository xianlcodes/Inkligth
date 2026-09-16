# syntax=docker/dockerfile:1
FROM python:3.11-slim
WORKDIR /app

# 1. 使用阿里云 Debian 镜像源，安装必需的图形库（opencv 需要 libGL）
RUN sed -i 's|http://deb.debian.org|http://mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxrender1 \
        libxext6 \
    && rm -rf /var/lib/apt/lists/*

# 2. 安装基础依赖（体积大、极少变动）
COPY requirements-base.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements-base.txt \
    --index-url https://download.pytorch.org/whl/cpu \
    --extra-index-url https://mirrors.aliyun.com/pypi/simple/

# 2.5 修补 pdf2zh 对腾讯云 SDK 的硬性导入
#     tencentcloud-sdk-python 3.0.1020 不含 TextTranslateRequest，
#     用 try/except 包裹，避免 pdf2zh 导入失败。
RUN python3 - <<'PY'
import pathlib
p = pathlib.Path("/usr/local/lib/python3.11/site-packages/pdf2zh/translator.py")
src = p.read_text()
old = """from tencentcloud.common import credential
from tencentcloud.tmt.v20180321.models import (
    TextTranslateRequest,
    TextTranslateResponse,
)
from tencentcloud.tmt.v20180321.tmt_client import TmtClient
"""
new = """try:
    from tencentcloud.common import credential
    from tencentcloud.tmt.v20180321.models import (
        TextTranslateRequest,
        TextTranslateResponse,
    )
    from tencentcloud.tmt.v20180321.tmt_client import TmtClient
    _TENCENT_TMT_AVAILABLE = True
except ImportError:
    credential = None
    TextTranslateRequest = None
    TextTranslateResponse = None
    TmtClient = None
    _TENCENT_TMT_AVAILABLE = False
"""
if old in src:
    p.write_text(src.replace(old, new))
    print("patched pdf2zh translator.py")
else:
    print("WARNING: target snippet not found, pdf2zh may already be patched")
PY

# 3. 安装应用依赖（变动频繁）
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt \
    -i https://mirrors.aliyun.com/pypi/simple/

# 4. 复制项目代码
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]