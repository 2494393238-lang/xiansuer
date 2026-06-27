"""
FastAPI 应用入口 — Your Voice Assistant Service

串联 ASR → LLM → TTS，提供 /ask /health /voices 接口。
"""

import io
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse

from app.config import config
from app.models.request_response import (
    AskRequest,
    AskResponse,
    HealthResponse,
)
from app.engines.asr_engine import ASREngine
from app.engines.llm_engine import LLMEngine
from app.engines.tts_engine import TTSEngine

# ============================================================================
# 日志
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [VoiceService] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("VoiceService")

# ============================================================================
# 引擎实例（lifespan 中初始化）
# ============================================================================
asr_engine: ASREngine = None
llm_engine: LLMEngine = None
tts_engine: TTSEngine = None

DEFAULT_SYSTEM_PROMPT = "你是一个有用的AI助手，请用简洁的中文回答。"

# ============================================================================
# OpenAPI 标签
# ============================================================================
tags_metadata = [
    {
        "name": "对话",
        "description": "核心智能对话接口，支持文本和语音双模输入输出。"
    },
    {
        "name": "系统",
        "description": "服务健康检查与状态监控。"
    },
    {
        "name": "音色",
        "description": "TTS 语音合成音色管理。"
    },
]

# ============================================================================
# Lifespan 管理
# ============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    global asr_engine, llm_engine, tts_engine

    logger.info("正在启动 Voice Assistant Service ...")
    asr_engine = ASREngine()
    llm_engine = LLMEngine()
    tts_engine = TTSEngine()
    logger.info("服务启动完成")

    yield

    logger.info("正在关闭服务 ...")
    # 清理资源（FunASR 模型、EdgeTTS 无需显式释放）


# ============================================================================
# FastAPI 实例
# ============================================================================
app = FastAPI(
    title="Your Voice Assistant Service",
    description=(
        "基于 **ASR（语音识别）+ LLM（大模型问答）+ TTS（语音合成）** "
        "的智能语音对话服务。\n\n"
        "支持文本和语音双模输入输出，核心对话接口 `/ask` 自动串联"
        " ASR → LLM → TTS 全链路处理。"
    ),
    version="1.0.0",
    contact={
        "name": "API Support",
    },
    license_info={
        "name": "MIT",
    },
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)


# ============================================================================
# POST /ask — 核心对话接口
# ============================================================================
@app.post(
    "/ask",
    summary="智能对话接口",
    description=(
        "核心对话接口，自动串联 ASR → LLM → TTS 全链路处理。\n\n"
        "**支持的输入模式：**\n"
        "- `text` — 直接传入文本（JSON body）\n"
        "- `audio` — 传入 WAV 音频二进制数据 + Query String 参数\n\n"
        "**支持的输出模式：**\n"
        "- `text` — 返回 JSON，包含 LLM 回复文本\n"
        "- `audio` — 返回 MP3 音频流（LLM 回复经 TTS 合成）\n\n"
        "**处理流程：**\n"
        "1. 输入解析：文本直接使用 / 音频经 ASR 转为文本\n"
        "2. LLM 推理：将文本送入大模型获取回复\n"
        "3. 输出：按 `output_type` 返回文本 JSON 或 MP3 音频\n\n"
        "**使用示例：**\n"
        "```json\n"
        '{"input_type":"text", "text":"你好", "output_type":"text"}\n'
        "```\n"
        "音频模式：`curl -X POST '/ask?input_type=audio&output_type=text'"
        " --data-binary @audio.wav`"
    ),
    response_description=(
        "根据 `output_type` 返回不同格式：\n"
        "- `text` → `AskResponse` JSON（包含 `success` 和 `text`）\n"
        "- `audio` → `audio/mpeg` 二进制音频流"
    ),
    responses={
        200: {
            "description": "成功 - 返回对话结果",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "text": "你好！我是 AI 助手，有什么可以帮你的？",
                        "audio_url": None,
                    }
                },
                "audio/mpeg": {
                    "description": "当 output_type=audio 时返回 MP3 音频"
                },
            },
        },
        400: {
            "description": "请求参数错误",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "text 模式下必须提供 text 字段"
                    }
                }
            },
        },
        503: {
            "description": "服务不可用（ASR 模型未加载 / LLM 未配置）",
            "content": {
                "application/json": {
                    "example": {"detail": "ASR 模型未加载"}
                }
            },
        },
    },
    tags=["对话"],
)
async def ask(request: Request):
    content_type = request.headers.get("content-type", "")

    # --- 解析请求体 ---
    if "application/json" in content_type:
        body_dict = await request.json()
        ask_req = AskRequest(**body_dict)
        audio_bytes = None
    else:
        # audio 二进制输入：从 query params 读取参数，body 为音频字节
        audio_bytes = await request.body()
        qp = request.query_params
        ask_req = AskRequest(
            input_type=qp.get("input_type", "audio"),
            output_type=qp.get("output_type", "text"),
            voice=qp.get("voice"),
            stream=qp.get("stream", "false").lower() == "true",
        )

    # --- Step 1: 获取用户文本 ---
    if ask_req.input_type == "audio":
        if not audio_bytes and "application/json" in content_type:
            raise HTTPException(
                status_code=400,
                detail="audio 模式需要二进制 body，或使用 multipart"
            )
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="未收到音频数据")
        if not asr_engine.is_loaded:
            raise HTTPException(status_code=503, detail="ASR 模型未加载")
        user_text = asr_engine.recognize(audio_bytes)
        logger.info(f"ASR 识别结果: {user_text}")
    else:
        if not ask_req.text:
            raise HTTPException(
                status_code=400, detail="text 模式下必须提供 text 字段"
            )
        user_text = ask_req.text

    # --- Step 2: LLM 问答 ---
    if not llm_engine.is_ready:
        raise HTTPException(status_code=503, detail="LLM 引擎未就绪")

    if ask_req.stream and ask_req.output_type == "text":
        # 流式文本输出 (SSE)
        async def stream_text():
            for token in llm_engine.ask_stream(
                user_text, system_prompt=DEFAULT_SYSTEM_PROMPT
            ):
                yield f"data: {token}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            stream_text(),
            media_type="text/event-stream",
        )

    # 非流式：获取完整回复
    reply_text = llm_engine.ask(
        user_text, system_prompt=DEFAULT_SYSTEM_PROMPT
    )
    logger.info(f"LLM 回复: {reply_text[:80]}...")

    # --- Step 3: TTS（可选） ---
    if ask_req.output_type == "audio":
        voice = ask_req.voice or tts_engine.default_voice
        mp3_bytes = tts_engine.synthesize(reply_text, voice=voice)
        return StreamingResponse(
            io.BytesIO(mp3_bytes),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "attachment; filename=reply.mp3"},
        )

    # --- Step 4: 返回 JSON ---
    return AskResponse(success=True, text=reply_text)


# ============================================================================
# GET /health — 健康检查
# ============================================================================
@app.get(
    "/health",
    response_model=HealthResponse,
    summary="服务健康检查",
    description=(
        "检查各引擎的运行状态：\n"
        "- `asr_loaded` — ASR 模型是否加载成功\n"
        "- `llm_ready` — LLM API 是否已配置且可连接\n"
        "- `tts_available` — TTS 引擎是否可用\n\n"
        "当所有引擎就绪时 `status` 为 `ok`，否则为 `degraded`。"
    ),
    response_description="各引擎状态",
    responses={
        200: {
            "description": "健康状态",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ok",
                        "asr_loaded": True,
                        "llm_ready": True,
                        "tts_available": True,
                    }
                }
            },
        },
    },
    tags=["系统"],
)
async def health():
    return HealthResponse(
        status="ok" if (asr_engine and asr_engine.is_loaded) else "degraded",
        asr_loaded=asr_engine.is_loaded if asr_engine else False,
        llm_ready=llm_engine.is_ready if llm_engine else False,
        tts_available=tts_engine.is_available if tts_engine else False,
    )


# ============================================================================
# GET /voices — 音色列表
# ============================================================================
@app.get(
    "/voices",
    summary="获取可用音色列表",
    description=(
        "返回当前 TTS 引擎（EdgeTTS）支持的所有常用中文音色，"
        "含普通话、粤语、台湾国语等多种口音。"
    ),
    response_description="音色字典，key 为短名称，value 为完整音色 ID",
    responses={
        200: {
            "description": "音色列表",
            "content": {
                "application/json": {
                    "example": {
                        "voices": {
                            "xiaoxiao": "zh-CN-XiaoxiaoNeural",
                            "xiaoyi": "zh-CN-XiaoyiNeural",
                            "yunjian": "zh-CN-YunjianNeural",
                        }
                    }
                }
            },
        },
    },
    tags=["音色"],
)
async def voices():
    return {"voices": tts_engine.list_voices() if tts_engine else {}}


# ============================================================================
# 启动入口
# ============================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=config.server.host,
        port=config.server.port,
        log_level="info",
    )
