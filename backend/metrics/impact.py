"""
期刊指标补充
"""
import json
import os
import re
from functools import lru_cache
from typing import Any

_DIR = os.path.dirname(__file__)
_JCR_PATH = os.path.join(_DIR, "jcr.json")
_SCI_PATH = os.path.join(_DIR, "sci.json")
_JCR_XLSX = os.path.join(_DIR, "..", "JCR.xlsx")
_SCI_XLSX = os.path.join(_DIR, "..", "SCI.xlsx")

_JCR_ORDER = ["Q1", "Q2", "Q3", "Q4"]
_CAS_ORDER = ["1区", "2区", "3区", "4区"]


def _normalize(name: str) -> str:
    """期刊名归一化，提升匹配率

    PubMed 返回的期刊名与分区表存在多种差异，需要统一处理：
    1) 大小写：\"Nature reviews. Clinical oncology\" vs \"Nature Reviews Clinical Oncology\"；
    2) 标点：点号/连字符/冒号等；
    3) 地区括注：\"Cancer communications (London, England)\"；
    4) 全称与缩写拼接：\"Cancer immunology, immunotherapy : CII\"。
    """
    name = name.strip()
    name = re.sub(r"\([^)]*\)", " ", name)   # 去除地区等括注
    if " : " in name:                        # 去除 PubMed 拼接的缩写部分
        name = name.split(" : ", 1)[0]
    name = name.lower()
    name = re.sub(r"[.\-:&/,]", " ", name)   # 点号/连字符/冒号/逗号等统一为空格
    name = re.sub(r"[^\w\s]", "", name)      # 去除其余标点
    name = re.sub(r"\s+", " ", name)         # 压缩空格
    return name.strip()


@lru_cache(maxsize=1)
def _jcr_index() -> dict[str, dict[str, Any]]:
    """JCR 索引：归一化期刊名 / 缩写 -> {if, quartile(Q1-Q4), abbr}"""
    with open(_JCR_PATH, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    idx: dict[str, dict[str, Any]] = {}
    for name, info in data.items():
        if name.startswith("_"):
            continue
        idx[_normalize(name)] = info
        abbr = info.get("abbr")
        if abbr:
            idx[_normalize(abbr)] = info
    return idx


@lru_cache(maxsize=1)
def _sci_index() -> dict[str, dict[str, Any]]:
    """SCI 索引：归一化期刊名 -> {quartile(1-4区)}"""
    with open(_SCI_PATH, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    return {
        _normalize(name): info
        for name, info in data.items()
        if not name.startswith("_")
    }


def lookup(journal_name: str | None) -> dict[str, Any]:
    """按期刊名查询指标：影响因子 / JCR 分区来自 JCR，中科院分区来自 SCI

    两个数据源相互独立：任一源未命中，其字段回退为 None / “未知”。
    """
    empty = {"if": None, "jcr_quartile": "未知", "sci_quartile": "未知", "matched": None}
    if not journal_name:
        return empty

    key = _normalize(journal_name)
    jcr = _jcr_index().get(key)
    sci = _sci_index().get(key)
    if not jcr and not sci:
        return empty

    return {
        "if": (jcr or {}).get("if"),
        "jcr_quartile": (jcr or {}).get("quartile", "未知"),
        "sci_quartile": (sci or {}).get("quartile", "未知"),
        "matched": journal_name,
    }


def build_from_excel() -> tuple[int, int]:
    """离线生成 jcr.json 与 sci.json（两份相互独立）

    需要 pandas / openpyxl，仅在本脚本离线执行时使用，运行时并不依赖它们。
    返回 (jcr 条目数, sci 条目数)。
    """
    import pandas as pd  # 延迟导入：运行时加载 JSON 不需要 pandas

    jcr_df = pd.read_excel(_JCR_XLSX, sheet_name="Sheet1")
    sci_df = pd.read_excel(_SCI_XLSX, sheet_name="完整版")

    # ---- JCR：影响因子 + JCR 分区 + 缩写 ----
    jcr: dict[str, Any] = {
        "_note": "来自 JCR.xlsx：影响因子JIF 与 JCR 分区（JIF分区 Q1-Q4）",
    }
    for name, abbr, ifv, q in zip(
        jcr_df["期刊名称"], jcr_df["期刊缩写"], jcr_df["影响因子JIF"], jcr_df["JIF分区"]
    ):
        if not isinstance(name, str) or not name.strip():
            continue
        info: dict[str, Any] = {}
        if pd.notna(ifv):
            info["if"] = round(float(ifv), 1)
        quartile = _clean_jcr_quartile(q)
        if quartile:
            info["quartile"] = quartile
        if isinstance(abbr, str) and abbr.strip():
            info["abbr"] = abbr.strip()
        if info:
            jcr[name.strip()] = info

    # ---- SCI：中科院分区 ----
    sci: dict[str, Any] = {"_note": "来自 SCI.xlsx：中科院期刊分区（2025 版，1-4 区）"}
    for name, part in zip(sci_df["期刊名称"], sci_df["2025分区"]):
        if not isinstance(name, str) or not name.strip():
            continue
        quartile = _clean_cas_quartile(part)
        if quartile:
            sci[name.strip()] = {"quartile": quartile}

    with open(_JCR_PATH, "w", encoding="utf-8") as f:
        json.dump(jcr, f, ensure_ascii=False)
    with open(_SCI_PATH, "w", encoding="utf-8") as f:
        json.dump(sci, f, ensure_ascii=False)

    _jcr_index.cache_clear()
    _sci_index.cache_clear()
    return len(jcr) - 1, len(sci) - 1


def _clean_jcr_quartile(value: Any) -> str | None:
    """把 JCR 分区值规整为 Q1-Q4；无效值返回 None"""
    text = str(value).strip().upper() if value is not None else ""
    return text if text in _JCR_ORDER else None


def _clean_cas_quartile(value: Any) -> str | None:
    """把中科院分区值规整为 "N区"；无效值返回 None"""
    try:
        n = int(float(value))
    except (TypeError, ValueError):
        return None
    return f"{n}区" if f"{n}区" in _CAS_ORDER else None


if __name__ == "__main__":
    jcr_n, sci_n = build_from_excel()
    print(f"[OK] jcr.json 已生成（{jcr_n} 条）、sci.json 已生成（{sci_n} 条）")
