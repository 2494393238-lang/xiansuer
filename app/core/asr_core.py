"""
ASR 核心模块 - FunASR 本地语音识别

从小智 ESP32-Server 项目中提取的纯 Python 语音识别模块。
支持 WAV/PCM 音频文件识别，去除了 WebSocket/设备通信等依赖。

依赖安装:
    pip install funasr soundfile

使用示例:
    python asr_core.py --model_dir models/SenseVoiceSmall --wav test.wav
"""

import os
import io
import wave
import re
import sys
import time
import logging
from typing import Optional, Tuple, Dict, Union

import numpy as np
from funasr import AutoModel

# ============================================================================
# 日志配置
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [ASR] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ASR")

# ============================================================================
# 情绪 → 表情映射 (来自原项目 utils.py)
# ============================================================================
EMOTION_EMOJI_MAP = {
    "HAPPY": "\U0001f642",      # 🙂
    "SAD": "\U0001f614",        # 😔
    "ANGRY": "\U0001f620",      # 😡
    "NEUTRAL": "\U0001f636",    # 😶
    "FEARFUL": "\U0001f630",    # 😰
    "DISGUSTED": "\U0001f922",  # 🤢
    "SURPRISED": "\U0001f632",  # 😲
    "EMO_UNKNOWN": "\U0001f636",# 😶
}


def lang_tag_filter(text: str) -> Union[Dict[str, str], str]:
    """
    解析 FunASR 识别结果，提取语种、情绪和纯文本。

    FunASR 输出格式：<|语种|><|情绪|><|事件|><|选项|>原文

    Returns:
        dict: 含 language/emotion/emoji/content 字段（有标签时）
        str: 纯文本（无标签时）
    """
    tag_pattern = r"<\|([^|]+)\|>"
    all_tags = re.findall(tag_pattern, text)
    clean_text = re.sub(tag_pattern, "", text).strip()

    if not all_tags:
        return clean_text

    language = all_tags[0] if len(all_tags) > 0 else "zh"
    emotion = all_tags[1] if len(all_tags) > 1 else "NEUTRAL"

    result = {
        "content": clean_text,
        "language": language,
        "emotion": emotion,
    }
    if emotion in EMOTION_EMOJI_MAP:
        result["emoji"] = EMOTION_EMOJI_MAP[emotion]

    return result


# ============================================================================
# PCM 工具函数 (来自原项目 base.py)
# ============================================================================
def pcm_to_wav(pcm_data: bytes, sample_rate: int = 16000, channels: int = 1,
               sample_width: int = 2) -> bytes:
    """将原始 PCM 数据转换为 WAV 格式字节"""
    if len(pcm_data) == 0:
        logger.warning("PCM 数据为空，无法转换为 WAV")
        return b""
    if len(pcm_data) % 2 != 0:
        pcm_data = pcm_data[:-1]

    wav_buffer = io.BytesIO()
    try:
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm_data)
        wav_buffer.seek(0)
        return wav_buffer.read()
    except Exception as e:
        logger.error(f"WAV 转换失败: {e}")
        return b""


def save_wav(wav_bytes: bytes, file_path: str) -> str:
    """将 WAV 字节写入磁盘"""
    os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(wav_bytes)
    logger.info(f"音频已保存: {file_path}")
    return file_path


# ============================================================================
# FunASR 语音识别器
# ============================================================================
class FunASRRecognizer:
    """
    基于 FunASR SenseVoiceSmall 的本地语音识别器。

    核心调用链:
        音频文件 → AutoModel.generate() → lang_tag_filter() → 识别结果
    """

    def __init__(self, model_dir: str, device: str = "cpu", max_retries: int = 2):
        """
        初始化识别器。

        Args:
            model_dir: SenseVoiceSmall 模型目录路径
            device: 推理设备 "cpu" / "cuda:0"
            max_retries: 识别失败最大重试次数
        """
        self.model_dir = model_dir
        self.device = device
        self.max_retries = max_retries

        logger.info(f"正在加载 FunASR 模型: {model_dir} (device={device})")
        t_start = time.time()

        model_kwargs = {
            "model": model_dir,
            "vad_kwargs": {"max_single_segment_time": 30000},
            "disable_update": True,
            "hub": "ms",
        }
        if device.startswith("cuda"):
            model_kwargs["device"] = device

        self.model = AutoModel(**model_kwargs)
        logger.info(f"模型加载完成，耗时 {time.time() - t_start:.1f}s")

    def recognize_wav(self, wav_path: str, language: str = "auto",
                      use_itn: bool = True) -> Union[Dict[str, str], str]:
        """
        识别 WAV 音频文件。

        Args:
            wav_path: WAV 文件路径
            language: 语种，默认自动检测
            use_itn: 是否启用逆文本归一化（中文数字→阿拉伯数字）

        Returns:
            dict: 含 language/emotion/content 字段
            str: 纯文本（无标签时）
        """
        if not os.path.exists(wav_path):
            raise FileNotFoundError(f"音频文件不存在: {wav_path}")

        logger.info(f"开始识别: {wav_path}")
        start_time = time.time()

        for attempt in range(self.max_retries):
            try:
                result = self.model.generate(
                    input=wav_path,
                    cache={},
                    language=language,
                    use_itn=use_itn,
                    batch_size_s=60,
                )
                raw_text = result[0]["text"]
                elapsed = time.time() - start_time

                parsed = lang_tag_filter(raw_text)
                if isinstance(parsed, dict):
                    logger.info(
                        f"识别完成 ({elapsed:.2f}s) | 语种: {parsed.get('language', '?')} "
                        f"| 情绪: {parsed.get('emotion', '?')} | 文本: {parsed['content']}"
                    )
                else:
                    logger.info(f"识别完成 ({elapsed:.2f}s) | 文本: {parsed}")
                return parsed

            except OSError as e:
                if attempt + 1 >= self.max_retries:
                    logger.error(f"识别失败（重试 {attempt + 1} 次后放弃）: {e}")
                    raise
                logger.warning(f"识别失败，重试 {attempt + 1}/{self.max_retries}: {e}")
                time.sleep(1)
            except Exception as e:
                logger.error(f"识别异常: {e}", exc_info=True)
                raise

    def recognize_pcm(self, pcm_data: bytes, sample_rate: int = 16000,
                      language: str = "auto", use_itn: bool = True
                      ) -> Union[Dict[str, str], str]:
        """
        识别原始 PCM 音频数据（16kHz, 16bit, mono）。

        Args:
            pcm_data: PCM 原始字节
            sample_rate: 采样率
            language: 语种
            use_itn: 是否启用 ITN

        Returns:
            dict 或 str: 识别结果
        """
        import tempfile
        wav_bytes = pcm_to_wav(pcm_data, sample_rate=sample_rate)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(wav_bytes)
            tmp_path = f.name

        try:
            return self.recognize_wav(tmp_path, language=language, use_itn=use_itn)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def recognize_numpy(self, audio: np.ndarray, sample_rate: int = 16000,
                        language: str = "auto", use_itn: bool = True
                        ) -> Union[Dict[str, str], str]:
        """
        识别 NumPy 数组格式的音频。

        Args:
            audio: 1D NumPy 数组，float32 范围 [-1, 1] 或 int16
            sample_rate: 采样率
            language: 语种
            use_itn: 是否启用 ITN

        Returns:
            dict 或 str: 识别结果
        """
        # 归一化处理
        if audio.dtype == np.int16:
            audio = audio.astype(np.float32) / 32768.0
        elif audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        if audio.max() > 1.0 or audio.min() < -1.0:
            audio = audio / max(abs(audio.max()), abs(audio.min()))

        logger.info(f"开始识别 (numpy, {len(audio) / sample_rate:.1f}s)")

        for attempt in range(self.max_retries):
            try:
                result = self.model.generate(
                    input=audio,
                    cache={},
                    language=language,
                    use_itn=use_itn,
                    batch_size_s=60,
                )
                raw_text = result[0]["text"]
                return lang_tag_filter(raw_text)
            except OSError as e:
                if attempt + 1 >= self.max_retries:
                    logger.error(f"识别失败: {e}")
                    raise
                logger.warning(f"重试 {attempt + 1}/{self.max_retries}: {e}")
                time.sleep(1)


# ============================================================================
# 命令行入口
# ============================================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="FunASR 本地语音识别")
    parser.add_argument("--model_dir", default="models/SenseVoiceSmall",
                        help="SenseVoiceSmall 模型目录")
    parser.add_argument("--wav", help="WAV 音频文件路径")
    parser.add_argument("--device", default="cpu", help="推理设备 (cpu/cuda:0)")
    parser.add_argument("--language", default="auto", help="语种 (auto/zh/en/...)")
    parser.add_argument("--no_itn", action="store_true", help="禁用 ITN")

    args = parser.parse_args()

    if not args.wav:
        print("=" * 60)
        print("FunASR 本地语音识别模块")
        print("=" * 60)
        print("\n使用示例:")
        print(f"  python {__file__} --model_dir models/SenseVoiceSmall --wav test.wav")
        print(f"  python {__file__} --model_dir models/SenseVoiceSmall --wav test.wav --device cuda:0")
        sys.exit(0)

    recognizer = FunASRRecognizer(args.model_dir, device=args.device)
    result = recognizer.recognize_wav(
        args.wav,
        language=args.language,
        use_itn=not args.no_itn,
    )

    print("\n" + "=" * 60)
    print("识别结果")
    print("=" * 60)
    if isinstance(result, dict):
        from pprint import pprint
        pprint(result)
    else:
        print(result)
