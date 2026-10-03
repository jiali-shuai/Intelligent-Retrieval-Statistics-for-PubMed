"""检索结果统计分析：数量 / 年份 / 分区 / 影响因子 / 高影响力文献"""
import datetime
from collections import Counter
from typing import Any

from metrics.impact import lookup

# 分区顺序：JCR 分区（Q1-Q4，来自 JCR）、中科院分区（1-4 区，来自 SCI）
JCR_ORDER = ["Q1", "Q2", "Q3", "Q4", "未知"]
CAS_ORDER = ["1区", "2区", "3区", "4区", "未知"]


def enrich(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """为每篇文献补充期刊影响因子与两种分区（JCR 分区 / 中科院分区）"""
    for a in articles:
        info = lookup(a.get("journal"))
        if info["if"] is None and a.get("journal_abbr"):
            info = lookup(a["journal_abbr"])
        a["impact_factor"] = info["if"]
        a["jcr_quartile"] = info["jcr_quartile"]
        a["sci_quartile"] = info["sci_quartile"]
        a["journal_matched"] = info["matched"]
    return articles


def build_stats(articles: list[dict[str, Any]], total: int, recent_years: int) -> dict[str, Any]:
    """构建总体统计：年份分布、分区分布、高产期刊、影响因子分布"""
    current_year = datetime.date.today().year

    # 年份分布
    year_counter = Counter(a["year"] for a in articles if a["year"])
    by_year = [{"year": y, "count": c} for y, c in sorted(year_counter.items())]

    # 分区分布：JCR 分区（Q1-Q4）与中科院分区（1-4 区）分别统计，互不混用
    jcr_counter = Counter(a["jcr_quartile"] for a in articles)
    by_jcr_quartile = [
        {"name": q, "value": jcr_counter.get(q, 0)}
        for q in JCR_ORDER if jcr_counter.get(q, 0) > 0
    ]
    cas_counter = Counter(a["sci_quartile"] for a in articles)
    by_sci_quartile = [
        {"name": q, "value": cas_counter.get(q, 0)}
        for q in CAS_ORDER if cas_counter.get(q, 0) > 0
    ]

    # 高产期刊 Top15
    journal_counter = Counter(a["journal"] for a in articles if a["journal"])
    by_journal = [{"name": n, "count": c} for n, c in journal_counter.most_common(15)]

    # 全体文献影响因子统计
    ifs = [a["impact_factor"] for a in articles if a["impact_factor"]]
    matched_count = len(ifs)
    avg_if = round(sum(ifs) / len(ifs), 2) if ifs else None
    max_if = round(max(ifs), 2) if ifs else None
    if_distribution = _if_bins(ifs)
    # 近 N 年文献影响因子统计
    cutoff = current_year - recent_years + 1
    recent_count = sum(1 for a in articles if a["year"] and int(a["year"]) >= cutoff)

    return {
        "total_hits": total,                      # PubMed 命中总数（检索式命中的全部文献量，可能远大于本次解析数）
        "fetched": len(articles),                 # 实际解析文献数（受 retmax/max_fetch 上限限制的抽样量）
        "recent_years": recent_years,             # “近 N 年”口径（前端展示与筛选依据）
        "recent_count": recent_count,             # 本次解析文献中，发表年份落在近 N 年内的篇数
        "if_matched": matched_count,              # 成功匹配到期刊影响因子的文献数（缺失者不计入 IF 统计）
        "if_coverage": round(matched_count / len(articles) * 100, 1) if articles else 0.0,  # 影响因子覆盖率（%，= if_matched / fetched）
        "avg_if": avg_if,                         # 已匹配文献的平均影响因子（仅基于 if_matched 子集，缺失值不参与）
        "max_if": max_if,                         # 已匹配文献中的最高影响因子（反映该领域顶级期刊水平）
        "by_year": by_year,                       # 年份分布：[{year, count}]，用于年份趋势折线图
        "by_jcr_quartile": by_jcr_quartile,       # JCR 分区分布：[{name, value}]，Q1-Q4 + 未知（来自 JCR），用于饼图
        "by_sci_quartile": by_sci_quartile,       # 中科院分区分布：[{name, value}]，1-4 区 + 未知（来自 SCI），用于饼图
        "by_journal": by_journal,                 # 高产期刊 Top15：[{name, count}]，本文样本中发文量最多的期刊
        "if_distribution": if_distribution,       # 影响因子分档分布：[{name, value}]，按 IF 数值区间统计，用于柱状图
    }


def _if_bins(ifs: list[float]) -> list[dict[str, Any]]:
    """影响因子分箱统计"""
    bins = [(0, 2), (2, 5), (5, 10), (10, 20), (20, 40), (40, 10 ** 9)]
    labels = ["0-2", "2-5", "5-10", "10-20", "20-40", ">40"]
    counts = [0] * len(bins)
    for v in ifs:
        for i, (lo, hi) in enumerate(bins):
            if lo <= v < hi:
                counts[i] += 1
                break
    return [{"name": labels[i], "value": counts[i]} for i in range(len(bins))]


def select_top_papers(
    articles: list[dict[str, Any]],
    recent_years: int,
    top_n: int = 100,
) -> tuple[list[dict[str, Any]], int]:
    """筛选近 N 年、按影响因子降序排列的 Top 文献"""
    current_year = datetime.date.today().year
    cutoff = current_year - recent_years + 1

    recent = [a for a in articles if a["year"] and int(a["year"]) >= cutoff]
    ranked = [a for a in recent if a["impact_factor"]]
    ranked.sort(key=lambda x: (x["impact_factor"], x["year"]), reverse=True)

    # 若期刊影响因子匹配不足，则退化为按年份排序，保证表格有内容
    if not ranked:
        ranked = sorted(recent, key=lambda x: x["year"], reverse=True)

    top = ranked[:top_n]
    return [_paper_brief(a, i + 1) for i, a in enumerate(top)], len(recent)


def _paper_brief(a: dict[str, Any], rank: int) -> dict[str, Any]:
    """把单篇文献整理成前端展示所需的精简结构

    a    : efetch 解析并 enrich 后的文献字典
    rank : 该文献在影响力排序中的名次（从 1 开始）
    """
    return {
        "rank": rank,                          # 影响力排名（按影响因子降序）
        "pmid": a["pmid"],                     # PubMed 唯一文献编号
        "title": a["title"],                   # 文献标题
        "journal": a["journal"],               # 期刊全称
        "year": a["year"],                     # 发表年份
        "impact_factor": a["impact_factor"],   # 期刊影响因子（来自 JCR，未匹配为 None）
        "jcr_quartile": a["jcr_quartile"],     # JCR 分区 Q1-Q4（来自 JCR，未匹配为“未知”）
        "sci_quartile": a["sci_quartile"],     # 中科院分区 1-4 区（来自 SCI，未匹配为“未知”）
        "authors": a["authors"][:6],           # 作者列表（截取前 6 位，避免过长）
        "author_count": len(a["authors"]),     # 作者总数（前端判断是否补“等”）
        "doi": a["doi"],                       # 数字对象标识符
        "url": a["url"],                       # PubMed 原文链接
        "abstract": a.get("abstract", ""),     # 摘要（供综述撰写与详情查看）
    }
