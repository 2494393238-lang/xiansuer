"""
TTS 引擎 — 封装 EdgeTTS

提供 synthesize() / synthesize_to_file() 接口，支持返回 MP3 字节或写入文件。
"""

import os
import asyncio
import logging

from app.core.tts_core import EdgeTTS as _CoreEdgeTTS, COMMON_VOICES

from app.config import config

logger = logging.getLogger("TTSEngine")


class TTSEngine:
    """TTS 引擎：封装 EdgeTTS，提供同步接口。"""

    def __init__(self):
        cfg = config.tts
        self._default_voice = cfg.voice
        self._output_dir = cfg.output_dir
        self._available = True

        os.makedirs(self._output_dir, exist_ok=True)
        logger.info(
            f"TTS 引擎初始化: voice={self._default_voice}, "
            f"output_dir={self._output_dir}"
        )

    @property
    def is_available(self) -> bool:
        return self._available

    @property
    def default_voice(self) -> str:
        return self._default_voice

    @staticmethod
    def list_voices() -> dict:
        """返回可用音色字典 {short_name: full_id}。"""
        return dict(COMMON_VOICES)

    def synthesize(self, text: str, voice: str = None) -> bytes:
        """
        将文本合成为 MP3 音频字节。

        Args:
            text: 待合成文本
            voice: 音色（不传使用默认音色）

        Returns:
            bytes: MP3 音频数据
        """
        tts = _CoreEdgeTTS(voice=voice or self._default_voice)
        return asyncio.run(tts.synthesize_to_bytes(text))

    def synthesize_to_file(self, text: str, output_path: str,
                           voice: str = None) -> str:
        """
        将文本合成为 MP3 并保存到文件。

        Args:
            text: 待合成文本
            output_path: 输出文件路径
            voice: 音色

        Returns:
            str: 输出文件路径
        """
        tts = _CoreEdgeTTS(voice=voice or self._default_voice)
        file_path, _ = asyncio.run(tts.synthesize(text, output_path))
        return file_path
