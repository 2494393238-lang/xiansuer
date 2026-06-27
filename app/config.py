"""
应用配置管理，支持从环境变量读取，并提供合理默认值。

环境变量命名规则: PREFIX_VOICE_* (ASR/LLM/TTS/SERVER)
"""

import os
from pydantic_settings import BaseSettings


class ASRConfig(BaseSettings):
    """ASR 语音识别配置"""
    model_dir: str = "iic/SenseVoiceSmall"
    device: str = "cpu"              # cpu / cuda:0
    sample_rate: int = 16000
    use_itn: bool = True             # 逆文本归一化

    model_config = {"env_prefix": "VOICE_ASR_", "extra": "ignore"}


class LLMConfig(BaseSettings):
    """LLM 大模型配置"""
    api_key: str = ""
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: float = 300.0

    model_config = {"env_prefix": "VOICE_LLM_", "extra": "ignore"}


class TTSConfig(BaseSettings):
    """TTS 语音合成配置"""
    voice: str = "zh-CN-XiaoxiaoNeural"
    output_dir: str = "output/tts"
    output_format: str = "mp3"

    model_config = {"env_prefix": "VOICE_TTS_", "extra": "ignore"}


class ServerConfig(BaseSettings):
    """服务器配置"""
    host: str = "0.0.0.0"
    port: int = 8080
    debug: bool = False

    model_config = {"env_prefix": "VOICE_SERVER_", "extra": "ignore"}


class Config(BaseSettings):
    """聚合配置"""
    asr: ASRConfig = ASRConfig()
    llm: LLMConfig = LLMConfig()
    tts: TTSConfig = TTSConfig()
    server: ServerConfig = ServerConfig()

    model_config = {"extra": "ignore"}


# 全局单例
config = Config()
