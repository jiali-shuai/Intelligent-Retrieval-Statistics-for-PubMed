"""
Tortoise ORM 初始化与同步桥接
"""
import asyncio
import threading
from typing import Any, Coroutine, TypeVar

from tortoise import Tortoise

from config import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER

T = TypeVar("T")

# MySQL 数据库配置（引擎 / 模型注册 / 时区）
DATABASE_CONFIG: dict[str, Any] = {
    "connections": {
        "default": {
            "engine": "tortoise.backends.mysql",
            "credentials": {
                "host": DB_HOST,
                "port": DB_PORT,
                "user": DB_USER,
                "password": DB_PASSWORD,
                "database": DB_NAME,
            },
        }
    },
    "apps": {
        "models": {
            "models": ["db.models"],
            "default_connection": "default",
        }
    },
    "use_tz": False,
    "timezone": "Asia/Shanghai",
}

_loop: asyncio.AbstractEventLoop | None = None
_loop_lock = threading.Lock()
_initialized = False


def enabled() -> bool:
    """是否已配置数据库（未配置则跳过持久化）"""
    return bool(DB_HOST and DB_NAME)


def _get_loop() -> asyncio.AbstractEventLoop:
    """获取（或惰性创建）后台常驻事件循环"""
    global _loop
    if _loop is None:
        with _loop_lock:
            if _loop is None:
                loop = asyncio.new_event_loop()
                threading.Thread(target=loop.run_forever, daemon=True).start()
                _loop = loop
    return _loop


def run_sync(coro: Coroutine[Any, Any, T]) -> T:
    """把协程提交到后台循环执行，并同步等待结果"""
    return asyncio.run_coroutine_threadsafe(coro, _get_loop()).result()


def init() -> None:
    """初始化 Tortoise 并自动建表；未配置数据库时打印提示并跳过"""
    global _initialized
    if not enabled():
        print("[WARN] 未配置 MySQL（DB_HOST/DB_NAME 为空），文献入库已跳过")
        return
    if _initialized:
        return
    run_sync(_init())
    _initialized = True
    print(f"[OK] 数据库连接成功（{DB_NAME}）")


async def _init() -> None:
    await Tortoise.init(config=DATABASE_CONFIG)
    await Tortoise.generate_schemas()


def close() -> None:
    """关闭数据库连接（服务停止时调用）"""
    global _initialized
    if not _initialized:
        return
    run_sync(Tortoise.close_connections())
    _initialized = False
