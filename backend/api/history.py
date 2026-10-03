"""
历史记录查询接口：查看历次分析询问
"""
from fastapi import APIRouter, HTTPException, Query

from db import engine as db_engine
from db import repository

router = APIRouter()

NO_DB_MSG = "未启用历史记录（未配置 MySQL）。"


@router.get("/api/history/runs")
def list_runs(
    limit: int = Query(20, ge=1, le=100, description="每页条数"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """分页查询历史询问列表（按时间倒序）"""
    if not db_engine.enabled():
        raise HTTPException(status_code=503, detail=NO_DB_MSG)

    total, items = repository.list_runs(limit=limit, offset=offset)
    return {"total": total, "limit": limit, "offset": offset, "items": items}


@router.get("/api/history/runs/{query_id}")
def get_run(query_id: str):
    """查询单次询问的完整记录（含 AI 生成的统计 / 词云 / 方向 / Top文献 / 综述）"""
    if not db_engine.enabled():
        raise HTTPException(status_code=503, detail=NO_DB_MSG)

    run = repository.get_run(query_id)
    if run is None:
        raise HTTPException(status_code=404, detail="未找到该历史记录")
    return run
