"""
Pydantic 请求 / 响应数据模型
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    """/ask 接口请求体 — 支持文本和音频双模输入。"""

    input_type: Literal["text", "audio"] = Field(
        description="输入模式：`text` 为直接文本输入，`audio` 为 WAV 音频二进制输入",
        examples=["text"],
    )
    text: Optional[str] = Field(
        default=None,
        description="文本内容（当 `input_type=text` 时必填）",
        examples=["你好，请介绍一下你自己"],
    )
    output_type: Literal["text", "audio"] = Field(
        default="text",
        description="输出模式：`text` 返回 JSON，`audio` 返回 MP3 音频流",
        examples=["text"],
    )
    voice: Optional[str] = Field(
        default=None,
        description="TTS 音色标识（仅 `output_type=audio` 时生效），不传使用默认音色",
        examples=["zh-CN-XiaoxiaoNeural"],
    )
    stream: bool = Field(
        default=False,
        description="LLM 是否启用流式输出（仅 `output_type=text` 时生效，SSE 格式）",
        examples=[False],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "input_type": "text",
                    "text": "你好，请介绍一下你自己",
                    "output_type": "text",
                    "stream": False,
                },
                {
                    "input_type": "audio",
                    "output_type": "text",
                    "voice": "zh-CN-XiaoxiaoNeural",
                    "stream": False,
                },
            ]
        }
    }


class AskResponse(BaseModel):
    """/ask 接口文本响应。"""

    success: bool = Field(
        description="请求是否成功",
        examples=[True],
    )
    text: str = Field(
        description="LLM 回复的文本内容",
        examples=["你好！我是 AI 助手，有什么可以帮你的？"],
    )
    audio_url: Optional[str] = Field(
        default=None,
        description="音频输出时的 URL（当前版本为直接流式返回，不使用此字段）",
        examples=[None],
    )


class HealthResponse(BaseModel):
    """/health 接口响应 — 各引擎运行状态。"""

    status: str = Field(
        description="整体状态：`ok` 所有引擎就绪，`degraded` 部分未就绪",
        examples=["ok"],
    )
    asr_loaded: bool = Field(
        description="ASR 模型是否加载成功",
        examples=[True],
    )
    llm_ready: bool = Field(
        description="LLM API 是否已配置且可连接",
        examples=[True],
    )
    tts_available: bool = Field(
        description="TTS 引擎是否可用",
        examples=[True],
    )
