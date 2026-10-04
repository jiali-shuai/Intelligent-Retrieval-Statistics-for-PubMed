"""PubMed 文献分析系统的配置文件"""
import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()


def get_env(key: str) -> str:
    """从 .env 获取必需配置，缺失则抛出错误"""
    value = os.getenv(key)
    if value is None:
        raise ValueError(f"缺少必需配置项: {key}，请在 .env 文件中设置")
    return value


def get_env_opt(key: str, default: str = "") -> str:
    """从 .env 获取可选配置，缺失则返回默认值"""
    value = os.getenv(key)
    return value if value else default


# ---------- NCBI E-utilities 配置 ----------
NCBI_API_KEY = get_env_opt("NCBI_API_KEY")
NCBI_EMAIL = get_env_opt("NCBI_EMAIL", "pubmed-analysis@example.com")

# ---------- 大模型配置（可选） ----------
DEEPSEEK_API_KEY = get_env_opt("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = get_env_opt("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = get_env_opt("DEEPSEEK_MODEL", "deepseek-flash")
# 深度思考强度（low/high/max），仅综述撰写环节开启；其余环节关闭思考以提速
DEEPSEEK_THINKING_EFFORT = get_env_opt("DEEPSEEK_THINKING_EFFORT", "high")

# ---------- MySQL 数据库配置（可选，未配置 DB_HOST/DB_NAME 则跳过入库） ----------
DB_HOST = get_env_opt("DB_HOST")
DB_PORT = int(get_env_opt("DB_PORT", "3306"))
DB_USER = get_env_opt("DB_USER")
DB_PASSWORD = get_env_opt("DB_PASSWORD")
DB_NAME = get_env_opt("DB_NAME")
