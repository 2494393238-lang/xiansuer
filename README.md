---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: def75172c756a0fcdccc1bbb3afa79c9_ef1dd73a6af211f1a0095254002afed2
    ReservedCode1: 3z5tc6i2Ci/8lmORKam2p1lduYIH9ATQTexTcEoez1Dn8gjE0Sadhvcz/YIOVgcQkhbEe0E8A0BVbvzowQ2hfLKB4E/OLMUsrGRqgbhpzuM41ftBE6A0nNlPleF/J9xi0K3L3Ll+W7cBqzFokkX1fkWVAjaCd8QmAIdJYU0uN14paiHatotspx71GCc=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: def75172c756a0fcdccc1bbb3afa79c9_ef1dd73a6af211f1a0095254002afed2
    ReservedCode2: 3z5tc6i2Ci/8lmORKam2p1lduYIH9ATQTexTcEoez1Dn8gjE0Sadhvcz/YIOVgcQkhbEe0E8A0BVbvzowQ2hfLKB4E/OLMUsrGRqgbhpzuM41ftBE6A0nNlPleF/J9xi0K3L3Ll+W7cBqzFokkX1fkWVAjaCd8QmAIdJYU0uN14paiHatotspx71GCc=
---



# Your Voice Assistant Service

基于 **ASR + LLM + TTS** 的语音对话服务，使用 FastAPI 构建。

## 目录结构

```
your-voice-assistant-service/
├── app/
│   ├── __init__.py
│   ├── main.py                   # FastAPI 入口，/ask /health /voices
│   ├── config.py                 # Pydantic Settings 配置管理
│   ├── engines/
│   │   ├── __init__.py
│   │   ├── asr_engine.py         # FunASR 语音识别封装
│   │   ├── llm_engine.py         # OpenAI 兼容 LLM 调用封装
│   │   └── tts_engine.py         # EdgeTTS 语音合成封装
│   └── models/
│       ├── __init__.py
│       └── request_response.py   # Pydantic 请求/响应模型
├── test_client.py                # 集成测试脚本
├── requirements.txt              # 项目依赖
└── README.md
```

## 安装

```bash
# 1. 创建虚拟环境（推荐）
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # Linux/macOS

# 2. 安装依赖
pip install -r requirements.txt

# 3. 下载 FunASR SenseVoiceSmall 模型
# 放入 models/SenseVoiceSmall/ 目录
```

## 配置

通过环境变量配置，变量名格式为 `VOICE_<模块>_<参数>`：

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `VOICE_ASR_MODEL_DIR` | `models/SenseVoiceSmall` | ASR 模型路径 |
| `VOICE_ASR_DEVICE` | `cpu` | 推理设备 (cpu / cuda:0) |
| `VOICE_LLM_API_KEY` | (空) | LLM API Key（必填） |
| `VOICE_LLM_BASE_URL` | `https://api.deepseek.com` | LLM API 地址 |
| `VOICE_LLM_MODEL` | `deepseek-chat` | 模型名 |
| `VOICE_TTS_VOICE` | `zh-CN-XiaoxiaoNeural` | 默认 TTS 音色 |
| `VOICE_SERVER_HOST` | `0.0.0.0` | 监听地址 |
| `VOICE_SERVER_PORT` | `8080` | 监听端口 |

## 启动

```bash
# 设置 LLM API Key（二选一）
set VOICE_LLM_API_KEY=sk-your-key-here          # Windows
export VOICE_LLM_API_KEY=sk-your-key-here        # Linux/macOS

# 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

## API 文档

启动后访问 http://localhost:8080/docs 查看自动生成的 Swagger 文档。

### POST /ask

核心对话接口，串联 ASR → LLM → TTS。

**请求体 (JSON):**

```json
{
  "input_type": "text",
  "text": "你好",
  "output_type": "text",
  "voice": null,
  "stream": false
}
```

**参数说明:**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| input_type | `"text"` / `"audio"` | 是 | 输入类型 |
| text | string | text 模式必填 | 文本内容 |
| output_type | `"text"` / `"audio"` | 否 | 默认 text |
| voice | string | 否 | TTS 音色 |
| stream | bool | 否 | LLM 流式输出 (仅 text 模式) |

**音频输入模式：** 发送二进制 WAV 数据作为 Body，参数通过 Query String 传递：

```bash
curl -X POST "http://localhost:8080/ask?input_type=audio&output_type=text" \
  --data-binary @test.wav
```

### GET /health

```json
{
  "status": "ok",
  "asr_loaded": true,
  "llm_ready": true,
  "tts_available": true
}
```

### GET /voices

返回可用 TTS 音色列表（19 个常用中文音色）。

## API 文档

启动服务后，通过以下地址访问自动生成的交互式 API 文档：

| 文档工具 | 地址 | 说明 |
|----------|------|------|
| **Swagger UI** | http://localhost:8080/docs | 交互式 API 调试界面，可直接在浏览器中测试所有接口 |
| **ReDoc** | http://localhost:8080/redoc | 更美观的 API 文档阅读界面，适合导出和分享 |

两个文档均自动包含：
- 请求/响应 Schema 定义
- 字段描述、示例值
- 错误码说明
- Try it out 在线调试

## Postman 测试

项目根目录提供了 `postman_collection.json`，可直接导入 Postman 进行测试。

### 导入步骤

1. 打开 Postman，点击左上角 **Import**
2. 选择 `C:\dama\your-voice-assistant-service\postman_collection.json`
3. 导入后，在 Collection 变量中将 `base_url` 设置为你的服务地址（默认 `http://localhost:8080`）

### 包含的请求

| 请求名 | 方法 | 说明 |
|--------|------|------|
| 文本问答 | POST /ask | 文本输入 + JSON 文本输出 |
| 文本转语音回复 | POST /ask | 文本输入 + MP3 音频输出 |
| 健康检查 | GET /health | 检查各引擎状态 |
| 获取音色列表 | GET /voices | 列出可用 TTS 音色 |
| 语音识别问答 | POST /ask | 音频输入 + 文本输出（需选择 WAV 文件） |

## 测试

```bash
# 启动服务后运行
python test_client.py

# 指定地址和音频文件
python test_client.py --base_url http://localhost:8080 --wav test.wav
```
*（内容由AI生成，仅供参考）*
