"""
统计员（StatsAgent）
"""
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage

from agent.llm import LLMError, parse_json
from agent.prompt_loader import load_prompt
from agent.tools import WORKSPACE, compute_stats, get_corpus

LABEL = "统计员"
PROMPT_FILE = "stats.txt"
TOOLS = [compute_stats, get_corpus]


class StatsAgent:
    """统计文献计量指标，并生成词云与研究方向"""

    def __init__(self, llm) -> None:
        self.llm = llm
        self.system_prompt = load_prompt(PROMPT_FILE)

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        keyword = state["keyword"]
        recent_years = state.get("recent_years", 5)

        # 确保工作区中有本轮检索结果（供工具读取）
        if not WORKSPACE.get("search"):
            WORKSPACE["search"] = {
                "total": state.get("total_hits", 0),
                "articles": state.get("articles", []),
            }

        parsed = self._run_agent(keyword, recent_years)
        if not isinstance(parsed, dict):
            raise LLMError("统计员返回结果无法解析")

        wordcloud = _clean_wordcloud(parsed.get("wordcloud"))
        directions = _clean_directions(parsed.get("directions"))
        summary = str(parsed.get("summary", "")).strip()
        if not wordcloud or not directions or not summary:
            raise LLMError("统计员未产出有效的词云 / 研究方向")

        stats = WORKSPACE.get("stats")
        if not stats:
            raise LLMError("统计员未完成计量统计")

        return {
            "stats": stats,
            "wordcloud": wordcloud,
            "directions": directions,
            "direction_summary": summary,
            "trace": [{
                "step": len(state.get("trace", [])) + 1,
                "agent": LABEL,
                "action": "统计与热点分析",
                "detail": (
                    f"平均 IF {stats.get('avg_if')}，最高 IF {stats.get('max_if')}，"
                    f"IF 覆盖率 {stats.get('if_coverage')}%；"
                    f"AI 提取：词云关键词 {len(wordcloud)} 个，研究方向 {len(directions)} 个"
                ),
            }],
        }

    def _run_agent(self, keyword: str, recent_years: int) -> Any:
        """由大模型调用工具并输出词云 / 方向 JSON"""
        user_input = (
            f"关键词：{keyword}\n"
            f"近 N 年：{recent_years}\n"
            f"请先调用 compute_stats 与 get_corpus，再按系统提示输出规定 JSON。"
        )
        try:
            agent = create_agent(model=self.llm, tools=TOOLS, system_prompt=self.system_prompt)
            messages = agent.invoke({"messages": [HumanMessage(content=user_input)]})["messages"]
        except LLMError:
            raise
        except Exception as e:
            raise LLMError(f"统计员调用失败：{e}") from e

        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
                try:
                    return parse_json(msg.content)
                except ValueError:
                    return None
        return None


def _clean_wordcloud(raw: Any) -> list[dict[str, Any]]:
    """校验并规整大模型返回的词云数据"""
    out: list[dict[str, Any]] = []
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not (isinstance(item, dict) and item.get("word")):
            continue
        try:
            weight = round(float(item.get("weight", 1)))
        except (TypeError, ValueError):
            weight = 1
        out.append({"word": str(item["word"]).strip(), "weight": weight})
    out.sort(key=lambda x: x["weight"], reverse=True)
    return out[:120]


def _clean_directions(raw: Any) -> list[dict[str, Any]]:
    """校验并规整大模型返回的研究方向数据"""
    out: list[dict[str, Any]] = []
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not (isinstance(item, dict) and item.get("name")):
            continue
        try:
            count = int(item.get("count", 0))
        except (TypeError, ValueError):
            count = 0
        out.append({"name": str(item["name"]).strip(), "count": count})
    return out[:20]
