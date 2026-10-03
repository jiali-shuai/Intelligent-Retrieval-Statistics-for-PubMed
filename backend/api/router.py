from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from api import analysis, history
from db import engine as db_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_engine.init()
    print("[OK] PubMed 文献分析服务已启动")
    yield
    db_engine.close()


app = FastAPI(title="PubMed 文献计量与综述分析系统", version="1.0.0", lifespan=lifespan)
api_router = APIRouter()

api_router.include_router(analysis.router, tags=["文献分析"])
api_router.include_router(history.router, tags=["历史记录"])


@app.get("/api/health")
def health():
    """健康检查"""
    return {"status": "ok"}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
