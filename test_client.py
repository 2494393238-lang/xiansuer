"""
测试脚本 — 覆盖 /ask /health /voices 五个典型场景。

用法:
    python test_client.py [--base_url http://localhost:8080]

依赖: pip install requests
"""

import os
import sys
import json
import argparse
from urllib.parse import urljoin

import requests


def color(text: str, code: str) -> str:
    """终端着色（可选）。"""
    colors = {"green": "32", "red": "31", "yellow": "33", "blue": "34"}
    c = colors.get(code, "0")
    return f"\033[{c}m{text}\033[0m"


def test_result(name: str, success: bool, summary: str = ""):
    status = color("PASS", "green") if success else color("FAIL", "red")
    print(f"\n[{status}] {name}")
    if summary:
        print(f"       {summary}")


def main():
    parser = argparse.ArgumentParser(description="Voice Service 测试脚本")
    parser.add_argument("--base_url", default="http://localhost:8080",
                        help="服务地址")
    parser.add_argument("--wav", default="",
                        help="用于音频测试的 WAV 文件路径")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")

    # ==================================================================
    # Test 1: 文本输入 + 文本输出
    # ==================================================================
    try:
        resp = requests.post(
            f"{base}/ask",
            json={
                "input_type": "text",
                "text": "你好，请用一句话介绍一下你自己",
                "output_type": "text",
            },
            timeout=60,
        )
        data = resp.json()
        success = resp.status_code == 200 and data.get("success")
        summary = f"status={resp.status_code}, reply={data.get('text', '')[:60]}..."
        test_result("文本输入 → 文本输出", success, summary)
    except Exception as e:
        test_result("文本输入 → 文本输出", False, str(e))

    # ==================================================================
    # Test 2: 音频输入 + 文本输出
    # ==================================================================
    if args.wav and os.path.exists(args.wav):
        try:
            with open(args.wav, "rb") as f:
                audio_data = f.read()
            resp = requests.post(
                f"{base}/ask?input_type=audio&output_type=text",
                data=audio_data,
                headers={"Content-Type": "application/octet-stream"},
                timeout=120,
            )
            data = resp.json()
            success = resp.status_code == 200 and data.get("success")
            summary = f"status={resp.status_code}, asr_text={data.get('text', '')[:60]}..."
            test_result("音频输入 → 文本输出", success, summary)
        except Exception as e:
            test_result("音频输入 → 文本输出", False, str(e))
    else:
        print(f"\n[{color('SKIP', 'yellow')}] 音频输入 → 文本输出 "
              f"(未提供 WAV 文件，使用 --wav 指定)")

    # ==================================================================
    # Test 3: 文本输入 + 音频输出
    # ==================================================================
    try:
        resp = requests.post(
            f"{base}/ask",
            json={
                "input_type": "text",
                "text": "你好，这是语音测试",
                "output_type": "audio",
            },
            timeout=120,
        )
        if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("audio/"):
            mp3_path = os.path.join(os.path.dirname(__file__) or ".", "test_output.mp3")
            with open(mp3_path, "wb") as f:
                f.write(resp.content)
            success = True
            summary = f"MP3 已保存到 {mp3_path} ({len(resp.content)} bytes)"
        else:
            success = False
            summary = f"status={resp.status_code}, content-type={resp.headers.get('content-type', '?')}"
        test_result("文本输入 → 音频输出", success, summary)
    except Exception as e:
        test_result("文本输入 → 音频输出", False, str(e))

    # ==================================================================
    # Test 4: 健康检查
    # ==================================================================
    try:
        resp = requests.get(f"{base}/health", timeout=5)
        data = resp.json()
        success = resp.status_code == 200
        summary = json.dumps(data, ensure_ascii=False)
        test_result("健康检查 GET /health", success, summary)
    except Exception as e:
        test_result("健康检查 GET /health", False, str(e))

    # ==================================================================
    # Test 5: 音色列表
    # ==================================================================
    try:
        resp = requests.get(f"{base}/voices", timeout=5)
        data = resp.json()
        success = resp.status_code == 200 and "voices" in data
        voice_count = len(data.get("voices", {}))
        summary = f"共 {voice_count} 个音色"
        test_result("音色列表 GET /voices", success, summary)
    except Exception as e:
        test_result("音色列表 GET /voices", False, str(e))

    print("\n测试完成。")


if __name__ == "__main__":
    main()
