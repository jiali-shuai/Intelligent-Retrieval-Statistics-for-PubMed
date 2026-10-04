"""
综述撰写员（ReviewAgent）
"""
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage

from agent.llm import LLMError, parse_json
from agent.prompt_loader import load_prompt
from agent.tools import WORKSPACE, get_review_materials

LABEL = "综述撰写员"
PROMPT_FILE = "review.txt"
TOOLS = [get_review_materials]


class ReviewAgent:
    """筛选高影响力文献并撰写中文综述报告"""

    def __init__(self, llm) -> None:
        self.llm = llm
        self.system_prompt = load_prompt(PROMPT_FILE)

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        recent_years = state.get("recent_years", 5)
        top_n = state.get("top_n", 100)

        bullets = self._run_agent(state, recent_years, top_n)
        if not bullets:
            raise LLMError("综述撰写员返回结果无法解析")

        top_papers = WORKSPACE.get("top_papers")
        if not top_papers:
            raise LLMError("综述撰写员未完成 Top 文献筛选")

        return {
            "top_papers": top_papers,
            "report": {"bullets": bullets, "source": "llm"},
            "trace": [{
                "step": len(state.get("trace", [])) + 1,
                "agent": LABEL,
                "action": "撰写综述",
                "detail": (
                    f"筛出近 {recent_years} 年 Top {len(top_papers)} 文献，"
                    f"生成 {len(bullets)} 条综述要点（AI 生成）"
                ),
            }],
        }

    def _run_agent(
        self, state: dict[str, Any], recent_years: int, top_n: int
    ) -> list[dict[str, str]] | None:
        """由大模型调用工具获取材料并撰写综述"""
        user_input = (
            f"关键词：{state['keyword']}\n"
            f"近 N 年：{recent_years}\n"
            f"top_n：{top_n}\n"
            f"请调用 get_review_materials 后按系统提示输出规定 JSON 数组。"
        )
        try:
            agent = create_agent(model=self.llm, tools=TOOLS, system_prompt=self.system_prompt)
            messages = agent.invoke({"messages": [HumanMessage(content=user_input)]})["messages"]
        except LLMError:
            raise
        except Exception as e:
            raise LLMError(f"综述撰写员调用失败：{e}") from e

        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
                return _parse_bullets(msg.content)
        return None


def _parse_bullets(text: str) -> list[dict[str, str]] | None:
    """解析综述要点 JSON；失败返回 None"""
    try:
        data = parse_json(text)
    except ValueError:
        return None
    if not isinstance(data, list):
        return None
    bullets = [
        {"title": str(item.get("title", "")), "content": str(item["content"])}
        for item in data
        if isinstance(item, dict) and item.get("content")
    ]
    return bullets or None
