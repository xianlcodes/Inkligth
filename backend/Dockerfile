FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（pdf2zh 的 opencv-python-headless 需要 libgl）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 安装 pdf2zh（PDF 原位翻译引擎）
RUN pip install --no-cache-dir pdf2zh

# 再安装 InkLight 专属依赖（不含 pdf2zh 已覆盖的包，避免版本冲突）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY . .

# 启动时自动下载布局模型（首次运行会缓存）
# EMBEDDING_MODEL_PATH 需在 .env 中配置或挂载外部卷

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
