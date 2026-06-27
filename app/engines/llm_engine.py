"""
LLM 引擎 — 封装 LLMEngine

提供 chat / ask / ask_stream 接口，自动从 config 读取 API 配置。
"""

import logging
from typing import Generator, List, Dict, Optional

from app.core.llm_core import LLMEngine as _CoreLLMEngine, build_messages

from app.config import config

logger = logging.getLogger("LLMEngine")


class LLMEngine:
    """LLM 引擎：封装大模型调用，支持流式/非流式问答。"""

    def __init__(self):
        cfg = config.llm
        self._ready = False

        if not cfg.api_key:
            logger.warning(
                "LLM API Key 未配置，请设置环境变量 VOICE_LLM_API_KEY"
            )
            self._core = None
            return

        try:
            self._core = _CoreLLMEngine(
                api_key=cfg.api_key,
                base_url=cfg.base_url,
                model=cfg.model,
                temperature=cfg.temperature,
                max_tokens=cfg.max_tokens,
                timeout=cfg.timeout,
            )
            self._ready = True
            logger.info(f"LLM 引擎初始化成功: {cfg.model} @ {cfg.base_url}")
        except Exception as e:
            logger.error(f"LLM 引擎初始化失败: {e}")
            self._core = None

    @property
    def is_ready(self) -> bool:
        return self._ready and self._core is not None

    def chat(self, messages: List[Dict[str, str]]) -> str:
        """多轮对话（非流式）。"""
        if not self.is_ready:
            raise RuntimeError("LLM 引擎未就绪")
        return self._core.chat(messages)

    def ask(self, question: str, system_prompt: str = None) -> str:
        """单轮问答（非流式）。"""
        if not self.is_ready:
            raise RuntimeError("LLM 引擎未就绪")
        return self._core.ask(question, system_prompt=system_prompt)

    def ask_stream(self, question: str,
                   system_prompt: str = None) -> Generator[str, None, None]:
        """单轮流式问答。"""
        if not self.is_ready:
            raise RuntimeError("LLM 引擎未就绪")
        yield from self._core.ask_stream(question, system_prompt=system_prompt)
