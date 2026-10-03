"""
PubMed 检索数据源入口（agent调用）
"""
from typing import Any

from pubmed import eutils

_eutils = eutils.EUtils()


def retrieve(
    term: str,
    retmax: int = 200,
    mindate: str | None = None,
    maxdate: str | None = None,
) -> tuple[int, list[dict[str, Any]]]:
    """
    统一检索入口，返回 (命中总数, 文献列表)
    """
    return _eutils.retrieve(term, retmax=retmax, mindate=mindate, maxdate=maxdate)
