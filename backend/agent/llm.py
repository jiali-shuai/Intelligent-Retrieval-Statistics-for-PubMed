"""
大模型配置与输出解析
"""
import json
import re
from typing import Any

from config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    DEEPSEEK_THINKING_EFFORT,
)


class LLMError(RuntimeError):
    """大模型不可用或调用失败"""

def is_available() -> bool:
    """是否已配置大模型"""
    return bool(DEEPSEEK_API_KEY)


def _build_llm(
    model: str,
    temperature: float | None = None,
    thinking: bool = False,
    effort: str = "high",
):
    """
    构造 ChatOpenAI 实例
    """
    if not DEEPSEEK_API_KEY:
        raise LLMError("未配置大模型（DEEPSEEK_API_KEY）")

    from langchain_openai import ChatOpenAI

    kwargs: dict = {
        "model": model,
        "openai_api_key": DEEPSEEK_API_KEY,
        "openai_api_base": DEEPSEEK_BASE_URL,
        "timeout": 120,          # 单次请求超时
        "max_retries": 2,        # 网络抖动自动重试
        "extra_body": {"thinking": {"type": "enabled" if thinking else "disabled"}},
    }
    if thinking:
        kwargs["reasoning_effort"] = effort
    elif temperature is not None:
        kwargs["temperature"] = temperature
    return ChatOpenAI(**kwargs)


def get_llm(temperature: float = 0.3):
    """获取快速对话模型实例（关闭深度思考，用于检索 / 统计等结构化任务）"""
    return _build_llm(DEEPSEEK_MODEL, temperature=temperature, thinking=False)


def get_reasoning_llm():
    """获取开启深度思考的模型实例（用于综述撰写等需要深度思考的环节）"""
    return _build_llm(DEEPSEEK_MODEL, thinking=True, effort=DEEPSEEK_THINKING_EFFORT)


def parse_json(text: Any) -> Any:
    """从模型输出中提取 JSON

    仅容忍 ```json 代码块围栏；内容为空或解析失败时抛出 ValueError。
    """
    if not isinstance(text, str):
        raise ValueError("LLM 返回内容非字符串")
    text = text.strip()
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if m:
        text = m.group(1).strip()
    if not text:
        raise ValueError("LLM 返回空内容")
    return json.loads(text)
