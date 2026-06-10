# syntax=docker/dockerfile:1
FROM python:3.11-slim
WORKDIR /app

# 1. 使用阿里云 Debian 镜像源，安装必需的图形库（opencv 需要 libGL）
RUN sed -i 's|http://deb.debian.org|http://mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        libglx-mesa0 \
        libglib2.0-0 \
        libsm6 \
        libxrender1 \
        libxext6 \
    && rm -rf /var/lib/apt/lists/*

# 2. 安装基础依赖（体积大、极少变动）
#    包含 PyTorch、pdf2zh 等，统一放入 requirements-base.txt，不单独安装
COPY requirements-base.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements-base.txt \
    --index-url https://download.pytorch.org/whl/cpu \
    --extra-index-url https://mirrors.aliyun.com/pypi/simple/

# 3. 安装应用依赖（变动频繁）
#    仅当 requirements.txt 本身变化时才重装此层
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt \
    -i https://mirrors.aliyun.com/pypi/simple/

# 4. 复制项目代码
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]