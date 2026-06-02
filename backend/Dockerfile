FROM python:3.11-slim
WORKDIR /app

# 1. 使用阿里云 Debian 镜像源，安装必需的图形库（opencv 需要 libgl1）
RUN sed -i 's|http://deb.debian.org|http://mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxrender1 \
        libxext6 \
    && rm -rf /var/lib/apt/lists/*

# 2. 安装项目依赖（CPU 版 PyTorch 强制从官方 CPU 索引拉取，不含任何 NVIDIA 包）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    --index-url https://download.pytorch.org/whl/cpu \
    --extra-index-url https://mirrors.aliyun.com/pypi/simple/

# 3. 安装 pdf2zh（同样使用阿里云镜像）
RUN pip install --no-cache-dir pdf2zh \
    -i https://mirrors.aliyun.com/pypi/simple/

# 4. 复制项目代码
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
