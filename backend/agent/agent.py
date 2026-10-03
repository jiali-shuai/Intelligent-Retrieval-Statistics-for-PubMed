"""
文献分析多智能体编排
"""
import operator
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, StateGraph

from agent.llm import LLMError, get_llm, get_reasoning_llm, parse_json
from agent.prompt_loader import load_prompt
from agent.review_agent import ReviewAgent
from agent.search_agent import SearchAgent
from agent.stats_agent import StatsAgent

MAX_ROUNDS = 2       # 最多检索轮次
WORKERS = ["search_agent", "stats_agent", "review_agent"]
FINISH = "FINISH"


class ResearchState(TypedDict, total=False):
    """文献分析任务的状态"""
    keyword: str                    # 用户原始关键词
    recent_years: int               # “近 N 年”口径
    max_fetch: int                  # 最多解析的文献数
    query_info: dict[str, Any]      # {"original","translated","query","source"}
    retrieval_round: int            # 已完成的检索轮次
    total_hits: int                 # 命中总数
    articles: list[dict[str, Any]]  # 已补充 IF/分区的文献列表
    stats: dict[str, Any]           # 计量统计
    wordcloud: list[dict[str, Any]]  # 词云数据
    directions: list[dict[str, Any]]  # 研究方向（主题词）
    direction_summary: str          # 研究方向概括
    top_papers: list[dict[str, Any]]  # 影响力 Top 文献
    report: dict[str, Any]            # 综述报告 {"bullets","source"}
    next_agent: str                 # 总管决定的下一个 agent（或 FINISH）
    trace: Annotated[list[dict[str, Any]], operator.add]  # 调度轨迹（追加式）


class SupervisorAgent:
    """总管：负责调度决策"""

    def route(self, state: dict[str, Any]) -> dict[str, Any]:
        """决定下一个执行的 agent，并记录调度轨迹"""
        # 1) 尚未检索：检索策略员构建检索式并执行检索
        if state.get("query_info") is None:
            return self._decide(state, "search_agent", "任务开始，指派检索策略员构建检索式并执行检索")

        # 2) 检索结果为空：允许放宽重试，达到上限则终止
        if not state.get("articles"):
            if state.get("retrieval_round", 0) < MAX_ROUNDS:
                return self._decide(
                    state, "search_agent",
                    "检索结果为空，指派检索策略员放宽检索式后重试",
                )
            return self._decide(state, FINISH, "多轮检索后仍无结果，终止编排")

        # 3) 已检索：判断样本是否充分，不足则放宽重试
        if state.get("stats") is None:
            sufficient, reason = self._judge_sufficiency(state)
            round_no = state.get("retrieval_round", 0)
            if not sufficient and round_no < MAX_ROUNDS:
                return self._decide(
                    state, "search_agent",
                    f"样本不足（{reason}），指派检索策略员放宽检索式后重试（第 {round_no + 1} 轮）",
                )
            note = "样本充分" if sufficient else f"样本仍不足但已达上限（{reason}），继续后续分析"
            return self._decide(state, "stats_agent", f"{note}，指派统计员开展统计与热点分析")

        # 4) 统计完成：综述撰写员筛选 Top 文献并撰写综述
        if state.get("report") is None:
            return self._decide(state, "review_agent", "统计完成，指派综述撰写员产出中文综述")

        return self._decide(state, FINISH, "全部任务完成，汇总结果并结束编排")

    def _decide(self, state: dict[str, Any], next_agent: str, reason: str) -> dict[str, Any]:
        return {
            "next_agent": next_agent,
            "trace": [{
                "step": len(state.get("trace", [])) + 1,
                "agent": "总管",
                "action": "调度",
                "detail": f"→ {next_agent}：{reason}",
            }],
        }

    def _judge_sufficiency(self, state: dict[str, Any]) -> tuple[bool, str]:
        """由大模型判断检索样本是否充分；调用失败抛出 LLMError"""
        total = state.get("total_hits", 0)
        fetched = len(state.get("articles", []))

        llm = get_llm(temperature=0.2)
        stats_ctx = {
            "keyword": state["keyword"],
            "query": state.get("query_info", {}).get("query", ""),
            "total_hits": total,
            "fetched": fetched,
            "recent_count": state.get("recent_count", fetched),
            "if_coverage": state.get("if_coverage", "未知"),
            "recent_years": state.get("recent_years", 5),
            "retrieval_round": state.get("retrieval_round", 1),
        }
        try:
            resp = llm.invoke(load_prompt("supervisor.txt").format(**stats_ctx))
        except LLMError:
            raise
        except Exception as e:
            raise LLMError(f"总管判断失败：{e}") from e

        try:
            data = parse_json(getattr(resp, "content", ""))
        except ValueError as e:
            raise LLMError(f"总管返回结果无法解析：{e}") from e
        if not isinstance(data, dict) or "sufficient" not in data:
            raise LLMError("总管返回结果无法解析")
        return bool(data["sufficient"]), str(data.get("reason", ""))


def _next_node(state: ResearchState) -> str:
    """条件边：读取总管给出的下一个节点"""
    return state.get("next_agent", FINISH)


class ResearchOrchestrator:
    """文献分析多智能体编排器"""

    def __init__(self) -> None:
        self.search_agent = SearchAgent(get_llm(temperature=0.2))
        self.stats_agent = StatsAgent(get_llm(temperature=0.3))
        self.review_agent = ReviewAgent(get_reasoning_llm())
        self.supervisor = SupervisorAgent()
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(ResearchState)

        # 决策中枢
        graph.add_node("supervisor", self.supervisor.route)
        # 成员 agent
        graph.add_node("search_agent", self.search_agent.run)
        graph.add_node("stats_agent", self.stats_agent.run)
        graph.add_node("review_agent", self.review_agent.run)

        graph.set_entry_point("supervisor")

        # 总管的条件边：分发给成员或结束
        graph.add_conditional_edges(
            "supervisor",
            _next_node,
            {**{w: w for w in WORKERS}, FINISH: END},
        )

        # 成员完成后统一回到总管，由总管决定下一步
        for w in WORKERS:
            graph.add_edge(w, "supervisor")

        return graph.compile()

    def invoke(self, keyword: str, recent_years: int, max_fetch: int) -> dict[str, Any]:
        """执行一次完整编排"""
        initial: ResearchState = {
            "keyword": keyword,
            "recent_years": recent_years,
            "max_fetch": max_fetch,
            "retrieval_round": 0,
            "trace": [],
        }
        return self.graph.invoke(initial, {"recursion_limit": 50})
