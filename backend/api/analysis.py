"""
文献分析接口：关键词 -> PubMed 检索 -> 统计分析 / 词云 / 方向 / Top100 / 综述
"""
import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agent.agent import ResearchOrchestrator
from agent.llm import LLMError, is_available as llm_available
from config import MAX_FETCH, RECENT_YEARS
from db import repository
from pubmed.eutils import PubMedError, is_available as pubmed_available

router = APIRouter()

AI_ERROR_MSG = "AI 出错，请稍后重试。"
PUBMED_ERROR_MSG = "PubMed 请求失败，请稍后再试。"
PUBMED_NO_KEY_MSG = "未配置 PubMed API Key（NCBI_API_KEY），无法发起检索。"


class AnalysisRequest(BaseModel):
    keyword: str = Field(..., min_length=1, description="检索关键词，支持中文/英文")
    recent_years: int = Field(RECENT_YEARS, ge=1, le=10, description="“近 N 年”口径（1-10）")
    max_fetch: int = Field(MAX_FETCH, ge=1, le=500, description="最多解析的文献数")


@router.post("/api/analysis/run")
def run_analysis(req: AnalysisRequest):
    """一站式文献计量分析（多智能体编排）"""
    keyword = req.keyword.strip()
    if not keyword:
        raise HTTPException(status_code=400, detail="关键词不能为空")

    if not llm_available():
        raise HTTPException(status_code=503, detail=AI_ERROR_MSG)

    if not pubmed_available():
        raise HTTPException(status_code=503, detail=PUBMED_NO_KEY_MSG)

    try:
        orchestrator = ResearchOrchestrator()
        result = orchestrator.invoke(keyword, req.recent_years, req.max_fetch)
    except PubMedError:
        raise HTTPException(status_code=503, detail=PUBMED_ERROR_MSG)
    except LLMError:
        raise HTTPException(status_code=503, detail=AI_ERROR_MSG)
    except Exception:
        raise HTTPException(status_code=503, detail=AI_ERROR_MSG)

    if not result.get("articles"):
        raise HTTPException(status_code=404, detail="未检索到相关文献，请更换关键词后重试")

    # 检索分析完成后入库（未配置 MySQL 时自动跳过；入库失败不影响分析结果）
    query_info = result.get("query_info", {})
    try:
        query_id = repository.start_run(keyword, req.recent_years, req.max_fetch)
        repository.save_articles(
            query_id,
            result.get("articles", []),
            result.get("total_hits", 0),
            query_info.get("query", ""),
            query_info.get("translated", ""),
        )
        repository.save_analysis(query_id, result)
    except Exception as e:
        print(f"[WARN] 文献入库失败：{e}")

    return {
        "keyword": keyword,
        "query": result["query_info"],
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "stats": result["stats"],
        "wordcloud": result.get("wordcloud", []),
        "directions": result.get("directions", []),
        "direction_summary": result.get("direction_summary", ""),
        "top_papers": result.get("top_papers", []),
        "report": result["report"],
        "orchestration": {
            "retrieval_round": result.get("retrieval_round", 1),
            "trace": result.get("trace", []),
        },
    }
