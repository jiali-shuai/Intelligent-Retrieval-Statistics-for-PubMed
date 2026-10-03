"""
检索策略员（SearchAgent）
"""
import datetime
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage

from agent.llm import LLMError, parse_json
from agent.prompt_loader import load_prompt
from agent.tools import WORKSPACE, search_pubmed
from pubmed.eutils import PubMedError

LABEL = "检索策略员"
PROMPT_FILE = "search.txt"
TOOLS = [search_pubmed]


class SearchAgent:
    """构建（或放宽）检索式并执行 PubMed 检索"""

    def __init__(self, llm) -> None:
        self.llm = llm
        self.system_prompt = load_prompt(PROMPT_FILE)

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        keyword = state["keyword"]
        recent_years = state.get("recent_years", 5)
        max_fetch = state.get("max_fetch", 100)
        round_no = state.get("retrieval_round", 0) + 1

        # 限定发表年份，聚焦“近 N 年”文献，避免按相关度排序混入大量陈旧文献
        current_year = datetime.date.today().year
        mindate = str(current_year - recent_years + 1)
        maxdate = str(current_year)

        WORKSPACE.pop("search", None)  # 每轮检索重置工作区

        info, result, detail = self._run_agent(
            state, keyword, mindate, maxdate, max_fetch, round_no
        )

        return {
            "query_info": info,
            "total_hits": result["total"],
            "articles": result["articles"],
            "retrieval_round": round_no,
            "trace": [{
                "step": len(state.get("trace", [])) + 1,
                "agent": LABEL,
                "action": "检索文献",
                "detail": (
                    f"{detail}；第 {round_no} 轮（{mindate}-{maxdate} 年）："
                    f"命中 {result['total']} 篇，解析 {len(result['articles'])} 篇"
                ),
            }],
        }

    def _run_agent(
        self,
        state: dict[str, Any],
        keyword: str,
        mindate: str,
        maxdate: str,
        max_fetch: int,
        round_no: int,
    ) -> tuple[dict[str, Any], dict[str, Any], str]:
        """由大模型自主调用检索工具"""
        user_input = (
            f"关键词：{keyword}\n"
            f"retmax：{max_fetch}\n"
            f"mindate：{mindate}\n"
            f"maxdate：{maxdate}\n"
        )
        if round_no > 1:
            user_input += (
                f"这是放宽重试的第 {round_no} 轮。\n"
                f"上一轮检索式：{state.get('query_info', {}).get('query', keyword)}\n"
                f"上一轮命中总数：{state.get('total_hits', 0)}\n"
                f"请放宽检索式以扩大召回。"
            )

        try:
            agent = create_agent(model=self.llm, tools=TOOLS, system_prompt=self.system_prompt)
            messages = agent.invoke({"messages": [HumanMessage(content=user_input)]})["messages"]
        except PubMedError:
            raise  # PubMed 请求失败：透传，由接口层提示稍后再试
        except LLMError:
            raise
        except Exception as e:
            raise LLMError(f"检索策略员调用失败：{e}") from e

        result = WORKSPACE.get("search")
        if result is None:
            raise LLMError("检索策略员未能调用检索工具")

        # 检索式：取自工具调用参数（比解析模型文字更可靠）
        query = None
        for msg in messages:
            for tc in getattr(msg, "tool_calls", None) or []:
                if tc.get("name") == "search_pubmed":
                    query = (tc.get("args") or {}).get("query")
                    break
            if query:
                break
        if not query:
            raise LLMError("检索策略员未能生成检索式")

        # 英文关键词：取自模型最后一条 JSON 回复
        translated = None
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
                data = None
                try:
                    data = parse_json(msg.content)
                except ValueError:
                    pass
                if isinstance(data, dict) and data.get("translated"):
                    translated = str(data["translated"])
                break
        if not translated:
            raise LLMError("检索策略员返回结果无法解析")

        info = {"original": keyword, "translated": translated, "query": query, "source": "llm"}
        detail = f"生成检索式：{query}" if round_no == 1 else f"放宽检索式（第 {round_no} 轮）：{query}"
        return info, result, detail
