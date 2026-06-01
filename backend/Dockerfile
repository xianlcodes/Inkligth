FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（pdf2zh 的 opencv-python-headless 需要 libgl）
RUN sed -i 's|http://deb.debian.org|http://mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 配置 pip 国内镜像（加速依赖下载）
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 先安装 InkLight 基础依赖（含 FastAPI、Pydantic 等）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 再安装 pdf2zh（自动覆盖 FastAPI、Pydantic 为它需要的版本）
RUN pip install --no-cache-dir pdf2zh

# 复制后端代码
COPY . .

# 启动时自动下载布局模型（首次运行会缓存）
# EMBEDDING_MODEL_PATH 需在 .env 中配置或挂载外部卷

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
