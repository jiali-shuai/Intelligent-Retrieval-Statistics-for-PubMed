"""
持久化仓储：登记询问、保存文献（同步接口，供编排流水线调用）
"""
from typing import Any
from uuid import uuid4

from db import engine
from db.models import Article, QueryArticle, QueryRun


def start_run(keyword: str, recent_years: int, max_fetch: int) -> str | None:
    """登记一次询问，返回 query_id；未启用持久化时返回 None"""
    if not engine.enabled():
        return None

    query_id = uuid4().hex

    async def _create() -> None:
        await QueryRun.create(
            query_id=query_id,
            keyword=keyword,
            recent_years=recent_years,
            max_fetch=max_fetch,
        )

    engine.run_sync(_create())
    return query_id


def save_articles(
    query_id: str | None,
    articles: list[dict[str, Any]],
    total_hits: int,
    query_string: str,
    translated: str,
) -> None:
    """
    把本次检索到的文献写入数据库
    """
    if not engine.enabled() or not query_id:
        return

    async def _save() -> None:
        run = await QueryRun.get_or_none(query_id=query_id)
        if run is None:
            return

        # 回填本次检索信息
        run.query_string = query_string or ""
        run.translated = translated or ""
        run.total_hits = total_hits
        run.fetched = len(articles)
        await run.save()

        # 规范化 pmid 并在本次内去重
        payload: list[tuple[str, dict[str, Any]]] = []
        seen: set[str] = set()
        for a in articles:
            pmid = str(a.get("pmid", "")).strip()
            if not pmid or pmid in seen:
                continue
            seen.add(pmid)
            payload.append((pmid, a))
        if not payload:
            return

        pmids = [pmid for pmid, _ in payload]
        existing = set(
            await Article.filter(pmid__in=pmids).values_list("pmid", flat=True)
        )

        # 新文献插入（已存在的复用，不覆盖）
        new_articles = [_to_article(a) for pmid, a in payload if pmid not in existing]
        if new_articles:
            await Article.bulk_create(new_articles, ignore_conflicts=True)

        # 记录本次询问与文献的关联（query 用实例，Tortoise 取其整型主键）
        links = [
            QueryArticle(query=run, article_id=pmid)
            for pmid, _ in payload
        ]
        await QueryArticle.bulk_create(links, ignore_conflicts=True)

    engine.run_sync(_save())


def save_analysis(query_id: str | None, result: dict[str, Any]) -> None:
    """
    把 AI 生成的分析结果写入对应询问：统计 / 词云 / 方向 / Top文献 / 综述
    """
    if not engine.enabled() or not query_id:
        return

    async def _save() -> None:
        run = await QueryRun.get_or_none(query_id=query_id)
        if run is None:
            return
        run.stats = result.get("stats") or {}
        run.wordcloud = result.get("wordcloud") or []
        run.directions = result.get("directions") or []
        run.direction_summary = result.get("direction_summary") or ""
        run.top_papers = result.get("top_papers") or []
        run.report = result.get("report") or {}
        await run.save()

    engine.run_sync(_save())


def list_runs(limit: int = 20, offset: int = 0) -> tuple[int, list[dict[str, Any]]]:
    """分页查询历史询问列表（按时间倒序），返回 (总数, 记录列表)

    未启用持久化时返回 (0, [])。
    """
    if not engine.enabled():
        return 0, []

    async def _query() -> tuple[int, list[dict[str, Any]]]:
        total = await QueryRun.all().count()
        runs = (
            await QueryRun.all()
            .order_by("-create_time")
            .offset(offset)
            .limit(limit)
        )
        items = [
            {
                "query_id": r.query_id,
                "keyword": r.keyword,
                "translated": r.translated or "",
                "query_string": r.query_string or "",
                "recent_years": r.recent_years,
                "max_fetch": r.max_fetch,
                "total_hits": r.total_hits,
                "fetched": r.fetched,
                "create_time": r.create_time.isoformat(timespec="seconds"),
            }
            for r in runs
        ]
        return total, items

    return engine.run_sync(_query())


def get_run(query_id: str) -> dict[str, Any] | None:
    """查询单次询问的完整记录（含 AI 生成结果）；未启用持久化或不存在时返回 None"""
    if not engine.enabled():
        return None

    async def _query() -> dict[str, Any] | None:
        r = await QueryRun.get_or_none(query_id=query_id)
        if r is None:
            return None
        return {
            "query_id": r.query_id,
            "keyword": r.keyword,
            "translated": r.translated or "",
            "query_string": r.query_string or "",
            "recent_years": r.recent_years,
            "max_fetch": r.max_fetch,
            "total_hits": r.total_hits,
            "fetched": r.fetched,
            "stats": r.stats or {},
            "wordcloud": r.wordcloud or [],
            "directions": r.directions or [],
            "direction_summary": r.direction_summary or "",
            "top_papers": r.top_papers or [],
            "report": r.report or {},
            "create_time": r.create_time.isoformat(timespec="seconds"),
        }

    return engine.run_sync(_query())


def _to_article(a: dict[str, Any]) -> Article:
    """把一篇文献字典转成 Article 实例（未保存）"""
    return Article(
        pmid=str(a.get("pmid", "")).strip(),
        title=a.get("title") or "",
        abstract=a.get("abstract") or "",
        journal=a.get("journal") or "",
        journal_abbr=a.get("journal_abbr") or "",
        year=str(a.get("year") or ""),
        authors=a.get("authors") or [],
        pub_types=a.get("pub_types") or [],
        mesh=a.get("mesh") or [],
        keywords=a.get("keywords") or [],
        doi=a.get("doi") or "",
        url=a.get("url") or "",
        impact_factor=a.get("impact_factor"),
        jcr_quartile=a.get("jcr_quartile") or "未知",
        sci_quartile=a.get("sci_quartile") or "未知",
    )
