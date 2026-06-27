# ============================================================================
# Your Voice Assistant Service — Dockerfile
# ============================================================================
# 构建:
#   docker build -t voice-assistant .
#
# 运行 (必需环境变量):
#   docker run -d -p 8080:8080 --name voice-assistant \
#     -e VOICE_LLM_API_KEY=sk-your-key \
#     voice-assistant
#
# 运行 (完整参数):
#   docker run -d -p 8080:8080 --name voice-assistant \
#     -e VOICE_LLM_API_KEY=sk-your-key \
#     -e VOICE_LLM_BASE_URL=https://api.deepseek.com \
#     -e VOICE_LLM_MODEL=deepseek-chat \
#     -e VOICE_ASR_DEVICE=cpu \
#     -v model_cache:/root/.cache/modelscope \
#     voice-assistant
#
# 查看日志:
#   docker logs -f voice-assistant
# ============================================================================

FROM python:3.10-slim

# 系统依赖：libsndfile1 (音频处理) + ffmpeg (音频编解码)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先复制依赖文件（利用 Docker 缓存层，代码变更时无需重装）
COPY requirements.txt .

# 使用清华 pip 镜像加速
RUN pip install --no-cache-dir \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    -r requirements.txt

# 复制项目代码
COPY app/ ./app/

# 暴露端口
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# 启动服务
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
