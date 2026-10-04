"""
成员 agent 可调用的工具
"""
import json
from typing import Any

from langchain_core.tools import tool

from pubmed import analyzer, client

WORKSPACE: dict[str, Any] = {}


@tool
def search_pubmed(query: str, retmax: int, mindate: str, maxdate: str) -> str:
    """检索 PubMed 并抓取文献元数据（已补充影响因子 / 分区）。

    参数：
    - query: PubMed 检索式
    - retmax: 最多解析的文献数
    - mindate / maxdate: 发表年份范围，如 "2022" / "2026"
    返回：JSON 摘要 {total, fetched, titles_preview}
    """
    total, articles = client.retrieve(query, retmax=retmax, mindate=mindate, maxdate=maxdate)
    analyzer.enrich(articles)
    WORKSPACE["search"] = {"total": total, "articles": articles}
    preview = [a.get("title", "") for a in articles[:8]]
    return json.dumps(
        {"total": total, "fetched": len(articles), "titles_preview": preview},
        ensure_ascii=False,
    )


@tool
def compute_stats(recent_years: int) -> str:
    """基于已检索到的文献做计量统计（数量 / 年份 / 分区 / 影响因子）。

    参数：
    - recent_years: “近 N 年”口径
    返回：JSON 关键指标
    """
    search = WORKSPACE.get("search", {})
    articles = search.get("articles", [])
    stats = analyzer.build_stats(articles, search.get("total", 0), recent_years)
    WORKSPACE["stats"] = stats
    return json.dumps(
        {
            k: stats.get(k)
            for k in ("total_hits", "fetched", "recent_count", "avg_if", "max_if", "if_coverage")
        },
        ensure_ascii=False,
    )


@tool
def get_corpus(limit: int = 150) -> str:
    """读取已检索文献的语料（标题 / 作者关键词 / MeSH 主题词），用于归纳研究热点。

    参数：
    - limit: 最多读取的文献数，默认 150
    返回：纯文本语料，每行一篇文献
    """
    articles = WORKSPACE.get("search", {}).get("articles", [])
    return _corpus_digest(articles, limit)


@tool
def get_review_materials(recent_years: int, top_n: int = 100) -> str:
    """筛选近 N 年高影响力 Top 文献，并返回综述所需的统计与文献摘要。

    参数：
    - recent_years: “近 N 年”口径
    - top_n: 保留的 Top 文献数量，默认 100
    返回：JSON，含 stats 与 papers（标题 / 期刊 / 年份 / IF / 摘要节选）
    """
    articles = WORKSPACE.get("search", {}).get("articles", [])
    papers, _ = analyzer.select_top_papers(articles, recent_years, top_n)
    WORKSPACE["top_papers"] = papers

    stats = WORKSPACE.get("stats", {})
    stats_brief = {
        k: stats.get(k)
        for k in ("total_hits", "recent_years", "recent_count", "fetched", "avg_if", "max_if")
    }
    papers_brief = [
        {
            "rank": p.get("rank"),
            "title": p.get("title"),
            "journal": p.get("journal"),
            "year": p.get("year"),
            "if": p.get("impact_factor"),
            "abstract": (p.get("abstract") or "").replace("\n", " "),
        }
        for p in papers[:30]
    ]
    return json.dumps({"stats": stats_brief, "papers": papers_brief}, ensure_ascii=False)


def _corpus_digest(articles: list[dict[str, Any]], limit: int = 150) -> str:
    """把文献整理成精简语料，控制 token 用量：标题 + 作者关键词 + MeSH 主题词"""
    lines = []
    for a in articles[:limit]:
        seg = [a.get("title", "").strip()]
        kws = a.get("keywords") or []
        if kws:
            seg.append("关键词: " + ", ".join(kws[:8]))
        mesh = a.get("mesh") or []
        if mesh:
            seg.append("主题词: " + "; ".join(mesh[:8]))
        lines.append("- " + " | ".join(s for s in seg if s))
    return "\n".join(lines) or "（无语料）"
