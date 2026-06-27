"""
TTS 核心模块 - EdgeTTS 语音合成

从小智 ESP32-Server 项目中提取的纯 Python TTS 模块。
基于 Microsoft Edge TTS 引擎，免费使用，音色丰富。

依赖安装:
    pip install edge-tts

使用示例:
    python tts_core.py --text "你好世界" --voice zh-CN-XiaoxiaoNeural --output hello.mp3
"""

import os
import sys
import asyncio
import logging
from typing import Optional, List, Tuple
from datetime import datetime
from uuid import uuid4

import edge_tts

# ============================================================================
# 日志配置
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [TTS] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("TTS")

# ============================================================================
# EdgeTTS 常用中文音色列表
# ============================================================================
COMMON_VOICES = {
    # --- 中文普通话 ---
    "xiaoxiao": "zh-CN-XiaoxiaoNeural",   # 晓晓 - 女声，活泼甜美
    "xiaoyi":   "zh-CN-XiaoyiNeural",     # 晓伊 - 女声，温柔
    "yunjian":  "zh-CN-YunjianNeural",    # 云健 - 男声，阳光
    "yunxi":    "zh-CN-YunxiNeural",      # 云希 - 男声，温暖
    "yunxia":   "zh-CN-YunxiaNeural",     # 云夏 - 男声，沉稳
    "xiaochen": "zh-CN-XiaochenNeural",   # 晓辰 - 女声，自然
    "xiaohan":  "zh-CN-XiaohanNeural",    # 晓涵 - 女声，知性
    "xiaomeng": "zh-CN-XiaomengNeural",   # 晓梦 - 女声，俏皮
    "xiaomo":   "zh-CN-XiaomoNeural",     # 晓墨 - 女声，冷静
    "xiaoxuan": "zh-CN-XiaoxuanNeural",   # 晓萱 - 女声，优雅
    "xiaoyan":  "zh-CN-XiaoyanNeural",    # 晓颜 - 女声，温柔
    "xiaoyou":  "zh-CN-XiaoyouNeural",    # 晓悠 - 女声，童声
    "xiaozhen": "zh-CN-XiaozhenNeural",   # 晓甄 - 女声，温柔
    "yunfeng":  "zh-CN-YunfengNeural",    # 云枫 - 男声，成熟
    "yunhao":   "zh-CN-YunhaoNeural",     # 云皓 - 男声，稳重

    # --- 粤语 ---
    "hiumaan":  "zh-HK-HiuMaanNeural",    # 曉曼 - 女声
    "wanlung":  "zh-HK-WanLungNeural",    # 雲龍 - 男声

    # --- 台湾国语 ---
    "hanhan":   "zh-TW-HsiaoChenNeural",  # 曉臻 - 女声
    "yunjhe":   "zh-TW-YunJheNeural",     # 雲哲 - 男声
}


def list_voices():
    """列出常用中文音色"""
    print("\n" + "=" * 60)
    print("EdgeTTS 常用中文音色列表")
    print("=" * 60)
    for name, voice_id in sorted(COMMON_VOICES.items()):
        print(f"  {name:12s}  {voice_id}")
    print("\n更多音色: https://learn.microsoft.com/zh-cn/azure/ai-services/speech-service/language-support")
    print()


# ============================================================================
# EdgeTTS 合成器
# ============================================================================
class EdgeTTS:
    """
    Microsoft Edge TTS 语音合成器。

    核心调用链:
        文本 → edge_tts.Communicate.stream() → 音频字节 → MP3 文件/内存

    特点:
        - 完全免费，无需 API Key
        - 音色丰富，支持多语言多口音
        - 简单易用
    """

    def __init__(self, voice: str = "zh-CN-XiaoxiaoNeural", output_dir: str = "output"):
        """
        初始化 TTS 合成器。

        Args:
            voice: 音色标识，如 "zh-CN-XiaoxiaoNeural"
            output_dir: 音频文件输出目录
        """
        self.voice = voice
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"EdgeTTS 初始化: voice={voice}, output_dir={output_dir}")

    def _make_filename(self, extension: str = ".mp3") -> str:
        """生成带时间戳的唯一文件名"""
        filename = f"tts-{datetime.now().strftime('%Y%m%d')}-{uuid4().hex[:8]}{extension}"
        return os.path.join(self.output_dir, filename)

    async def synthesize(self, text: str, output_path: Optional[str] = None
                         ) -> Tuple[str, bytes]:
        """
        将文本合成为语音。

        Args:
            text: 待合成的文本
            output_path: 输出文件路径（可选，为空则生成到 output_dir）

        Returns:
            Tuple[str, bytes]: (文件路径, 音频二进制数据)

        Raises:
            Exception: 合成失败时抛出
        """
        if not text or not text.strip():
            raise ValueError("文本内容为空")

        communicate = edge_tts.Communicate(text.strip(), voice=self.voice)

        if output_path is None:
            output_path = self._make_filename()

        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        # 先收集全部音频数据，再一次性写入
        audio_chunks: List[bytes] = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])

        audio_bytes = b"".join(audio_chunks)

        if not audio_bytes:
            raise Exception("EdgeTTS 返回了空音频数据")

        with open(output_path, "wb") as f:
            f.write(audio_bytes)

        duration_ms = len(audio_bytes) * 8 / 128000 * 1000  # 估算时长 (128kbps MP3)
        logger.info(
            f"语音合成完成: {output_path} "
            f"({len(audio_bytes)} bytes, ~{duration_ms / 1000:.1f}s)"
        )
        return output_path, audio_bytes

    async def synthesize_to_bytes(self, text: str) -> bytes:
        """
        合成语音并返回二进制数据（不写文件）。

        Args:
            text: 待合成文本

        Returns:
            bytes: MP3 音频数据
        """
        if not text or not text.strip():
            raise ValueError("文本内容为空")

        communicate = edge_tts.Communicate(text.strip(), voice=self.voice)
        audio_bytes = b""

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_bytes += chunk["data"]

        if not audio_bytes:
            raise Exception("EdgeTTS 返回了空音频数据")

        logger.info(f"语音合成完成: {len(audio_bytes)} bytes (仅内存)")
        return audio_bytes

    async def batch_synthesize(self, texts: List[str],
                               output_dir: Optional[str] = None
                               ) -> List[Tuple[str, str, bytes]]:
        """
        批量合成多个文本。

        Args:
            texts: 文本列表
            output_dir: 输出目录

        Returns:
            List[Tuple[str, str, bytes]]: [(文本, 文件路径, 音频数据), ...]
        """
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        results = []
        for i, text in enumerate(texts):
            output_path = None
            if output_dir:
                output_path = os.path.join(output_dir, f"sentence_{i + 1:03d}.mp3")
            file_path, audio_bytes = await self.synthesize(text, output_path)
            results.append((text, file_path, audio_bytes))

        logger.info(f"批量合成完成: {len(results)} 句")
        return results


# ============================================================================
# 同步封装
# ============================================================================
def text_to_speech(text: str, voice: str = "zh-CN-XiaoxiaoNeural",
                   output_path: Optional[str] = None) -> str:
    """
    同步接口：将文本转为 MP3 语音文件。

    Args:
        text: 文本内容
        voice: 音色名称
        output_path: 输出路径

    Returns:
        str: MP3 文件路径
    """
    tts = EdgeTTS(voice=voice)
    file_path, _ = asyncio.run(tts.synthesize(text, output_path))
    return file_path


# ============================================================================
# 命令行入口
# ============================================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="EdgeTTS 语音合成")
    parser.add_argument("--text", help="待合成文本")
    parser.add_argument("--file", help="从文件读取文本（每行一句）")
    parser.add_argument("--voice", default="zh-CN-XiaoxiaoNeural",
                        help="音色标识 (默认: zh-CN-XiaoxiaoNeural)")
    parser.add_argument("--output", help="输出 MP3 文件路径")
    parser.add_argument("--output_dir", default="output",
                        help="批量输出目录 (默认: output)")
    parser.add_argument("--list", action="store_true", help="列出常用音色")

    args = parser.parse_args()

    if args.list:
        list_voices()
        sys.exit(0)

    tts = EdgeTTS(voice=args.voice)

    if args.file:
        # 批量模式：从文件读取
        if not os.path.exists(args.file):
            print(f"错误: 文件不存在 {args.file}")
            sys.exit(1)
        with open(args.file, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        print(f"从 {args.file} 读取了 {len(lines)} 行文本")

        async def batch_run():
            results = await tts.batch_synthesize(lines, args.output_dir)
            print(f"\n合成完成，共 {len(results)} 个文件:")
            for text, path, _ in results:
                print(f"  [{path}] {text[:40]}{'...' if len(text) > 40 else ''}")

        asyncio.run(batch_run())

    elif args.text:
        # 单句模式
        async def single_run():
            path, audio = await tts.synthesize(args.text, args.output)
            print(f"语音文件: {path}")
            print(f"大小: {len(audio)} bytes")

        asyncio.run(single_run())

    else:
        # 交互模式
        print("=" * 60)
        print("EdgeTTS 交互模式 (输入 quit 退出)")
        print(f"音色: {args.voice}")
        print("=" * 60)

        async def interactive():
            idx = 0
            while True:
                try:
                    text = input("\n文本: ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nBye!")
                    break
                if not text:
                    continue
                if text.lower() in ("quit", "exit", "q"):
                    break

                idx += 1
                output_path = args.output or os.path.join(
                    args.output_dir, f"sentence_{idx:03d}.mp3"
                )
                path, audio = await tts.synthesize(text, output_path)
                print(f"  -> {path} ({len(audio)} bytes)")

        asyncio.run(interactive())
