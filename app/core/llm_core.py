"""
LLM 核心模块 - OpenAI 兼容接口大模型问答

从小智 ESP32-Server 项目中提取的纯 Python LLM 调用模块。
支持所有 OpenAI 兼容 API 的大模型服务（DeepSeek/Qwen/ChatGLM/Doubao 等）。

依赖安装:
    pip install openai httpx

使用示例:
    python llm_core.py --api_key sk-xxx --base_url https://api.deepseek.com --model deepseek-chat
"""

import sys
import logging
from typing import Optional, List, Dict, Generator, Tuple, Any, Union
from urllib.parse import urlparse

import httpx
from openai import OpenAI
from openai.types import CompletionUsage

# ============================================================================
# 日志配置
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [LLM] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("LLM")

# ============================================================================
# 需要禁用思考模式的平台域名
# ============================================================================
THINKING_DISABLED_DOMAINS = {
    "aliyuncs.com": {"enable_thinking": False},
    "bigmodel.cn": {"thinking": {"type": "disabled"}},
    "moonshot.cn": {"thinking": {"type": "disabled"}},
    "volces.com": {"thinking": {"type": "disabled"}},
}


# ============================================================================
# ChatMessage / Dialogue 类型定义
# ============================================================================
ChatMessage = Dict[str, str]          # {"role": "user", "content": "..."}
Dialogue = List[ChatMessage]


def build_messages(system_prompt: Optional[str] = None,
                   user_prompt: str = "",
                   history: Optional[List[Dict[str, str]]] = None) -> Dialogue:
    """
    构建标准对话格式的消息列表。

    Args:
        system_prompt: 系统提示词
        user_prompt: 用户消息
        history: 历史对话 [{"role": "user/assistant", "content": "..."}, ...]

    Returns:
        完整的消息列表
    """
    messages: Dialogue = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    if history:
        messages.extend(history)
    if user_prompt:
        messages.append({"role": "user", "content": user_prompt})
    return messages


# ============================================================================
# LLM 引擎
# ============================================================================
class LLMEngine:
    """
    OpenAI 兼容接口的大模型调用引擎。

    支持的服务:
        - DeepSeek:    base_url=https://api.deepseek.com
        - 通义千问:    base_url=https://dashscope.aliyuncs.com/compatible-mode/v1
        - ChatGLM:     base_url=https://open.bigmodel.cn/api/paas/v4/
        - 豆包:        base_url=https://ark.cn-beijing.volces.com/api/v3
        - Ollama 本地: base_url=http://localhost:11434/v1
        - 任意 OpenAI 兼容服务
    """

    def __init__(self, api_key: str, base_url: str, model: str,
                 temperature: Optional[float] = None,
                 max_tokens: Optional[int] = None,
                 top_p: Optional[float] = None,
                 frequency_penalty: Optional[float] = None,
                 timeout: float = 300.0):
        """
        初始化 LLM 引擎。

        Args:
            api_key: API 密钥
            base_url: API 基础地址
            model: 模型名称
            temperature: 生成温度 (0~2)
            max_tokens: 最大生成 Token 数
            top_p: 核采样参数
            frequency_penalty: 频率惩罚
            timeout: 请求超时秒数
        """
        self.model = model
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.frequency_penalty = frequency_penalty

        custom_timeout = httpx.Timeout(timeout)
        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=custom_timeout)

        logger.info(f"LLM 引擎初始化: model={model}, base_url={base_url}")

    def _apply_thinking_disabled(self, params: dict) -> None:
        """根据域名自动禁用思考模式"""
        domain = urlparse(self.base_url).netloc
        for disabled_domain, extra in THINKING_DISABLED_DOMAINS.items():
            if disabled_domain in domain:
                params.setdefault("extra_body", {}).update(extra)
                logger.info(f"已为 {domain} 禁用思考模式")
                break

    def _add_optional_params(self, params: dict, **overrides) -> None:
        """添加可选参数（跳过 None）"""
        for key, default in [
            ("max_tokens", self.max_tokens),
            ("temperature", self.temperature),
            ("top_p", self.top_p),
            ("frequency_penalty", self.frequency_penalty),
        ]:
            value = overrides.get(key, default)
            if value is not None:
                params[key] = value

    def chat_stream(self, messages: Dialogue, **kwargs
                    ) -> Generator[str, None, None]:
        """
        流式对话，逐步返回生成的文本 Token。

        Args:
            messages: 对话消息列表
            **kwargs: 可选参数覆盖 (temperature, max_tokens, top_p, frequency_penalty)

        Yields:
            str: 文本片段
        """
        request_params = {
            "model": self.model,
            "messages": self._normalize_dialogue(messages),
            "stream": True,
        }
        self._add_optional_params(request_params, **kwargs)
        self._apply_thinking_disabled(request_params)

        response = self.client.chat.completions.create(**request_params)
        is_active = True

        try:
            for chunk in response:
                try:
                    delta = chunk.choices[0].delta if chunk.choices else None
                    content = getattr(delta, "content", "") if delta else ""
                except (IndexError, AttributeError):
                    content = ""
                if not content:
                    continue

                # 处理 <｜end▁of▁thinking｜> / think 标签
                if "<｜end▁of▁thinking｜>" in content:
                    is_active = False
                    content = content.split(" response")[0]
                if "<｜end▁of▁thinking｜>" in content:
                    is_active = True
                    content = content.split(" response")[-1]
                if is_active and content:
                    yield content
        finally:
            response.close()

    def chat(self, messages: Dialogue, **kwargs) -> str:
        """
        非流式对话，返回完整响应文本。

        Args:
            messages: 对话消息列表
            **kwargs: 可选参数覆盖

        Returns:
            完整的响应文本
        """
        result_parts = []
        for token in self.chat_stream(messages, **kwargs):
            result_parts.append(token)
        return "".join(result_parts)

    def ask(self, prompt: str, system_prompt: Optional[str] = None,
            history: Optional[List[Dict[str, str]]] = None, **kwargs) -> str:
        """
        快捷提问接口：一问一答。

        Args:
            prompt: 用户问题
            system_prompt: 系统提示词
            history: 历史对话
            **kwargs: 其他参数

        Returns:
            模型回答文本
        """
        messages = build_messages(system_prompt, prompt, history)
        return self.chat(messages, **kwargs)

    def ask_stream(self, prompt: str, system_prompt: Optional[str] = None,
                   history: Optional[List[Dict[str, str]]] = None, **kwargs
                   ) -> Generator[str, None, None]:
        """
        快捷流式提问接口。

        Yields:
            str: 实时文本 Token
        """
        messages = build_messages(system_prompt, prompt, history)
        yield from self.chat_stream(messages, **kwargs)

    def chat_with_tools(self, messages: Dialogue, functions: List[dict],
                        **kwargs) -> Generator[Tuple[str, Optional[Any]], None, None]:
        """
        Function Calling 流式调用。

        Yields:
            Tuple[str, Optional[Any]]: (文本Token, tool_calls或None)
        """
        request_params = {
            "model": self.model,
            "messages": self._normalize_dialogue(messages),
            "stream": True,
            "tools": functions,
        }
        self._add_optional_params(request_params, **kwargs)
        self._apply_thinking_disabled(request_params)

        stream = self.client.chat.completions.create(**request_params)
        try:
            for chunk in stream:
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    content = getattr(delta, "content", "")
                    tool_calls = getattr(delta, "tool_calls", None)
                    yield content, tool_calls
                elif isinstance(getattr(chunk, "usage", None), CompletionUsage):
                    usage = chunk.usage
                    logger.info(
                        f"Token 消耗: 输入={usage.prompt_tokens}, "
                        f"输出={usage.completion_tokens}, "
                        f"总计={usage.total_tokens}"
                    )
        finally:
            stream.close()

    @staticmethod
    def _normalize_dialogue(dialogue: Dialogue) -> Dialogue:
        """修复缺失 content 字段的消息"""
        for msg in dialogue:
            if "role" in msg and "content" not in msg:
                msg["content"] = ""
        return dialogue


# ============================================================================
# 命令行入口
# ============================================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="LLM 大模型问答模块")
    parser.add_argument("--api_key", required=True, help="API 密钥")
    parser.add_argument("--base_url", required=True, help="API 基础地址")
    parser.add_argument("--model", required=True, help="模型名称")
    parser.add_argument("--prompt", help="提问内容，不传则进入交互模式")
    parser.add_argument("--system_prompt", help="系统提示词")
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--max_tokens", type=int, default=2048)
    parser.add_argument("--stream", action="store_true", help="启用流式输出")

    args = parser.parse_args()

    engine = LLMEngine(
        api_key=args.api_key,
        base_url=args.base_url,
        model=args.model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    )

    if args.prompt:
        if args.stream:
            print(">>> ", end="", flush=True)
            for token in engine.ask_stream(args.prompt, system_prompt=args.system_prompt):
                print(token, end="", flush=True)
            print()
        else:
            answer = engine.ask(args.prompt, system_prompt=args.system_prompt)
            print(answer)
    else:
        print("=" * 60)
        print("LLM 交互模式 (输入 quit 退出)")
        print(f"模型: {args.model} | 地址: {args.base_url}")
        print("=" * 60)

        history: List[Dict[str, str]] = []
        while True:
            try:
                user_input = input("\nYou: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nBye!")
                break
            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                break

            print("AI: ", end="", flush=True)
            full_response = []
            for token in engine.ask_stream(user_input, history=history,
                                           system_prompt=args.system_prompt):
                print(token, end="", flush=True)
                full_response.append(token)
            print()

            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": "".join(full_response)})
