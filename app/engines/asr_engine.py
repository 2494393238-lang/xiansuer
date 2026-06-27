"""
ASR 引擎 — 封装 FunASRRecognizer

加载模型、提供 recognize() 和 recognize_file() 两个核心接口。
"""

import os
import logging
import tempfile
from typing import Union, Dict

from app.core.asr_core import FunASRRecognizer

from app.config import config

logger = logging.getLogger("ASREngine")


class ASREngine:
    """ASR 引擎：封装 FunASR 模型的加载与推理。"""

    def __init__(self):
        cfg = config.asr
        self._loaded = False

        try:
            logger.info(
                f"正在加载 ASR 模型: {cfg.model_dir} (device={cfg.device})"
            )
            self._recognizer = FunASRRecognizer(
                model_dir=cfg.model_dir,
                device=cfg.device,
            )
            self._loaded = True
            logger.info("ASR 模型加载成功")
        except Exception as e:
            logger.error(f"ASR 模型加载失败: {e}")
            self._recognizer = None

    @property
    def is_loaded(self) -> bool:
        return self._loaded and self._recognizer is not None

    def recognize(self, audio_bytes: bytes) -> str:
        """
        接收原始 WAV 音频字节，返回识别文本。

        Args:
            audio_bytes: WAV 格式的音频数据

        Returns:
            str: 识别出的文本
        """
        if not self.is_loaded:
            raise RuntimeError("ASR 模型未加载，无法识别")

        # 写入临时文件
        with tempfile.NamedTemporaryFile(
            suffix=".wav", delete=False
        ) as f:
            f.write(audio_bytes)
            tmp_path = f.name

        try:
            result = self._recognizer.recognize_wav(
                tmp_path,
                use_itn=config.asr.use_itn,
            )
            if isinstance(result, dict):
                return result.get("content", "")
            return str(result)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def recognize_file(self, file_path: str) -> str:
        """
        从音频文件路径识别。

        Args:
            file_path: WAV 文件路径

        Returns:
            str: 识别文本
        """
        if not self.is_loaded:
            raise RuntimeError("ASR 模型未加载，无法识别")

        result = self._recognizer.recognize_wav(
            file_path,
            use_itn=config.asr.use_itn,
        )
        if isinstance(result, dict):
            return result.get("content", "")
        return str(result)
