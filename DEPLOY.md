---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: def75172c756a0fcdccc1bbb3afa79c9_e292b2586af311f1a99c5254007bceed
    ReservedCode1: yKAUxaHS6LPjN+Z0dnstYQa+88KZl04/ZoTeneh7AX9cPFWHLrkFN3UGpk2WTzUKSEMah2sYqIlUOSH43F73+aj4MgYImwmbxYV5Ky/lndOItJVEoFnvBybEzByR1McLzYbjmZfsF1Z9jJVgYfvxHBdxDhEHrWUxIUbNziUf2KcU+stPKKGKfICl3Ts=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: def75172c756a0fcdccc1bbb3afa79c9_e292b2586af311f1a99c5254007bceed
    ReservedCode2: yKAUxaHS6LPjN+Z0dnstYQa+88KZl04/ZoTeneh7AX9cPFWHLrkFN3UGpk2WTzUKSEMah2sYqIlUOSH43F73+aj4MgYImwmbxYV5Ky/lndOItJVEoFnvBybEzByR1McLzYbjmZfsF1Z9jJVgYfvxHBdxDhEHrWUxIUbNziUf2KcU+stPKKGKfICl3Ts=
---

# Your Voice Assistant Service — 部署指南

## 环境要求

| 项目 | 最低要求 | 推荐配置 |
|------|----------|----------|
| Python | 3.10+ | 3.11 |
| 操作系统 | Linux / macOS / Windows | Ubuntu 22.04 |
| 内存 | 4 GB | 8 GB+ |
| 磁盘 | 5 GB（含模型） | 10 GB+ |
| GPU（可选） | NVIDIA + CUDA 11.8+ | T4 / A10 及以上 |

## 安装步骤

### 本地部署

```bash
# 1. 进入项目目录
cd your-voice-assistant-service

# 2. 创建虚拟环境
python -m venv venv

# 3. 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux / macOS:
source venv/bin/activate

# 4. 安装依赖
pip install -r requirements.txt
```

### Docker 部署

```bash
# 1. 构建镜像
docker build -t voice-assistant .

# 2. 运行容器（最小配置）
docker run -d -p 8080:8080 --name voice-assistant \
  -e VOICE_LLM_API_KEY=sk-your-key \
  voice-assistant

# 3. 运行容器（完整配置）
docker run -d -p 8080:8080 --name voice-assistant \
  -e VOICE_LLM_API_KEY=sk-your-key \
  -e VOICE_LLM_BASE_URL=https://api.deepseek.com \
  -e VOICE_LLM_MODEL=deepseek-chat \
  -e VOICE_ASR_DEVICE=cpu \
  -e VOICE_TTS_VOICE=zh-CN-XiaoxiaoNeural \
  -v model_cache:/root/.cache/modelscope \
  voice-assistant

# 4. 查看日志
docker logs -f voice-assistant
```

### Docker Compose 部署（推荐）

```bash
# 1. 设置环境变量（Linux/macOS）
export VOICE_LLM_API_KEY=sk-your-key

# Windows CMD:
set VOICE_LLM_API_KEY=sk-your-key

# 2. 启动服务
docker-compose up -d

# 3. 查看日志
docker-compose logs -f

# 4. 停止服务
docker-compose down
```

## 配置说明

所有配置通过环境变量设置，变量名格式为 `VOICE_<模块>_<参数>`：

### ASR（语音识别）

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `VOICE_ASR_MODEL_DIR` | `models/SenseVoiceSmall` | FunASR 模型路径（首次运行自动下载） |
| `VOICE_ASR_DEVICE` | `cpu` | 推理设备：`cpu` / `cuda:0` |
| `VOICE_ASR_SAMPLE_RATE` | `16000` | 音频采样率 |
| `VOICE_ASR_USE_ITN` | `true` | 是否启用逆文本归一化（中文数字→阿拉伯数字） |

### LLM（大模型）

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `VOICE_LLM_API_KEY` | (空) | **必填** — LLM API 密钥 |
| `VOICE_LLM_BASE_URL` | `https://api.deepseek.com` | API 基础地址 |
| `VOICE_LLM_MODEL` | `deepseek-chat` | 模型名称 |
| `VOICE_LLM_TEMPERATURE` | `0.7` | 生成温度 (0~2) |
| `VOICE_LLM_MAX_TOKENS` | `2048` | 最大输出 Token 数 |
| `VOICE_LLM_TIMEOUT` | `300` | 请求超时秒数 |

### TTS（语音合成）

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `VOICE_TTS_VOICE` | `zh-CN-XiaoxiaoNeural` | 默认音色 |
| `VOICE_TTS_OUTPUT_DIR` | `output/tts` | 音频输出目录 |
| `VOICE_TTS_OUTPUT_FORMAT` | `mp3` | 输出格式 |

### 服务

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `VOICE_SERVER_HOST` | `0.0.0.0` | 监听地址 |
| `VOICE_SERVER_PORT` | `8080` | 监听端口 |
| `VOICE_SERVER_DEBUG` | `false` | 调试模式 |

## 启动服务

### 开发模式

```bash
# 单进程，自动重载
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### 生产模式

```bash
# 多 Worker（Linux 推荐，Windows 不支持 --workers 参数）
uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 4

# 或用 Docker
docker-compose up -d
```

## 验证服务

### 健康检查

```bash
curl http://localhost:8080/health
```

期望响应：
```json
{"status":"ok","asr_loaded":true,"llm_ready":true,"tts_available":true}
```

### API 文档

浏览器打开以下地址：

- **Swagger UI**（交互式调试）：http://localhost:8080/docs
- **ReDoc**（只读文档）：http://localhost:8080/redoc

### 测试文本问答

```bash
curl -X POST http://localhost:8080/ask \
  -H "Content-Type: application/json" \
  -d '{"input_type":"text","text":"你好","output_type":"text"}'
```

期望响应：
```json
{"success":true,"text":"你好！有什么可以帮你的吗？","audio_url":null}
```

### 测试语音合成

```bash
curl -X POST http://localhost:8080/ask \
  -H "Content-Type: application/json" \
  -d '{"input_type":"text","text":"你好世界","output_type":"audio"}' \
  -o reply.mp3
```

### 测试音频识别（需准备 WAV 文件）

```bash
curl -X POST "http://localhost:8080/ask?input_type=audio&output_type=text" \
  --data-binary @audio.wav
```

## 常见问题

### FunASR 模型下载慢？

SenseVoiceSmall 模型约 300MB，首次运行会自动从 ModelScope 下载。国内用户可通过设置镜像加速：

```bash
export MODELSCOPE_CACHE=/path/to/cache
```

Docker 部署时模型缓存在 `model_cache` volume 中，重启不会重复下载。

### CUDA GPU 加速？

```bash
# 安装 GPU 版 PyTorch 后设置
export VOICE_ASR_DEVICE=cuda:0
```

### 端口被占用？

修改 `VOICE_SERVER_PORT` 环境变量或 `docker-compose.yml` 中的端口映射。

### LLM 调用失败？

1. 检查 `VOICE_LLM_API_KEY` 是否正确
2. 确认网络可访问 `VOICE_LLM_BASE_URL`
3. 查看容器日志：`docker logs voice-assistant`

