"""
PubMed 检索实现（基于 NCBI E-utilities）
"""
import time
import xml.etree.ElementTree as ET
from typing import Any

import requests

from config import NCBI_API_KEY, NCBI_EMAIL

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

_REQUEST_INTERVAL = 0.12   # 配置 Key 后频率上限 10 次/秒，按 8 次/秒节流

_MAX_ATTEMPTS = 3          # 单次请求最多尝试次数（含首次）
_BACKOFF_BASE = 1.0        # 指数退避基数（秒）：1s → 2s
_RETRY_STATUS = {429, 500, 502, 503, 504}   # 可重试的 HTTP 状态码


class PubMedError(RuntimeError):
    """PubMed 检索失败（未配置 Key 或请求出错）"""


def is_available() -> bool:
    """是否已配置 NCBI API Key（必须配置才允许请求）"""
    return bool(NCBI_API_KEY)


def _is_retryable(e: requests.RequestException) -> bool:
    """判断请求异常是否值得重试（超时 / 连接错误 / 限流 / 服务端错误）"""
    if isinstance(e, (requests.Timeout, requests.ConnectionError)):
        return True
    if isinstance(e, requests.HTTPError) and e.response is not None:
        return e.response.status_code in _RETRY_STATUS
    return False


def _retry_delay(e: requests.RequestException, attempt: int) -> float:
    """指数退避等待时长；若响应带 Retry-After 则取其较大值"""
    delay = _BACKOFF_BASE * (2 ** (attempt - 1))
    if isinstance(e, requests.HTTPError) and e.response is not None:
        ra = e.response.headers.get("Retry-After")
        if ra and ra.isdigit():
            delay = max(delay, int(ra))
    return delay


class EUtils:
    """
    封装 NCBI E-utilities 的 esearch / efetch 两个接口
    """

    def __init__(
        self,
        api_key: str | None = NCBI_API_KEY,
        email: str = NCBI_EMAIL,
        tool: str = "pubmed-analysis-demo",
    ) -> None:
        self.api_key = api_key
        self.email = email
        self.tool = tool
        self._last_ts = 0.0   # 上次请求时间戳

    # -------------------------------------------------------------- 请求层

    def _get(self, url: str, params: dict[str, Any], timeout: int) -> requests.Response:
        """
        发起 GET 请求（自动注入公共参数并节流）

        对超时 / 连接错误 / 限流(429) / 服务端错误(5xx) 做指数退避重试；
        其余错误（如参数错误 4xx）立即抛出，不重试。
        """
        full_params = {"tool": self.tool, "email": self.email, "api_key": self.api_key, **params}
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            self._throttle()
            try:
                resp = requests.get(url, params=full_params, timeout=timeout)
                resp.raise_for_status()
                return resp
            except requests.RequestException as e:
                if not _is_retryable(e) or attempt == _MAX_ATTEMPTS:
                    raise PubMedError(f"PubMed 请求失败（尝试 {attempt} 次）：{e}") from e
                time.sleep(_retry_delay(e, attempt))
        raise PubMedError("PubMed 请求失败")  # 理论不可达

    def esearch(
        self,
        term: str,
        retmax: int = 200,
        mindate: str | None = None,
        maxdate: str | None = None,
        sort: str = "relevance",
    ) -> dict[str, Any]:
        """
        检索 PubMed
        """
        params = {
            "db": "pubmed",
            "term": term,
            "retmode": "json",
            "retmax": retmax,
            "sort": sort,
        }
        if mindate:
            params["mindate"] = mindate
            params["datetype"] = "pdat"
            if maxdate:
                params["maxdate"] = maxdate

        resp = self._get(ESEARCH_URL, params, timeout=30)
        return resp.json().get("esearchresult", {})

    def efetch(self, pmids: list[str], batch_size: int = 200) -> list[bytes]:
        """
        按 PMID 分批获取文献详情

        单批失败（含重试后仍失败）不会中断整体：跳过该批、继续其余批次，
        仅在全部批次都失败时才抛出 PubMedError。
        """
        chunks: list[bytes] = []
        batches = [pmids[i:i + batch_size] for i in range(0, len(pmids), batch_size)]
        for idx, batch in enumerate(batches, start=1):
            params = {"db": "pubmed", "id": ",".join(batch), "retmode": "xml"}
            try:
                chunks.append(self._get(EFETCH_URL, params, timeout=60).content)
            except PubMedError as e:
                print(f"[WARN] efetch 第 {idx}/{len(batches)} 批失败，已跳过：{e}")
        if batches and not chunks:
            raise PubMedError(f"efetch 全部 {len(batches)} 批请求均失败")
        return chunks

    # -------------------------------------------------------------- 解析层

    @staticmethod
    def parse_esearch(raw: dict[str, Any]) -> tuple[int, list[str]]:
        """把 esearch 原始响应分解为 (命中总数, PMID 列表)"""
        total = int(raw.get("count", 0))
        pmids = raw.get("idlist", [])
        return total, pmids

    @classmethod
    def parse_efetch(cls, raw: bytes) -> list[dict[str, Any]]:
        """把单批 efetch 原始 XML 分解为文献字典列表"""
        root = ET.fromstring(raw)
        return [cls._parse_article(art) for art in root.findall(".//PubmedArticle")]

    # -------------------------------------------------------------- 流程层

    def retrieve(
        self,
        term: str,
        retmax: int = 200,
        mindate: str | None = None,
        maxdate: str | None = None,
    ) -> tuple[int, list[dict[str, Any]]]:
        """
        检索并获取文献详情
        """
        if not is_available():
            raise PubMedError("未配置 NCBI API Key")

        total, pmids = self.parse_esearch(
            self.esearch(term, retmax=retmax, mindate=mindate, maxdate=maxdate)
        )
        articles: list[dict[str, Any]] = []
        for chunk in self.efetch(pmids):
            articles.extend(self.parse_efetch(chunk))
        return total, articles

    # -------------------------------------------------------------- 内部工具

    def _throttle(self) -> None:
        """按 NCBI 频率限制进行请求节流"""
        wait = _REQUEST_INTERVAL - (time.time() - self._last_ts)
        if wait > 0:
            time.sleep(wait)
        self._last_ts = time.time()

    @staticmethod
    def _text(node: ET.Element | None) -> str:
        """提取节点全部文本并去除首尾空白（itertext 可穿透内嵌子标签）"""
        return "".join(node.itertext()).strip() if node is not None else ""

    @classmethod
    def _parse_article(cls, art: ET.Element) -> dict[str, Any]:
        """
        从单个 PubmedArticle 节点中提取所需字段，拍平为一层字典
        """
        medline = art.find("MedlineCitation")
        article = medline.find("Article")

        # 摘要：可能存在多个 AbstractText（带 Label 的分段摘要）
        abstract_parts = []
        for ab in article.findall(".//Abstract/AbstractText"):
            label = ab.get("Label")
            txt = cls._text(ab)
            abstract_parts.append(f"{label}: {txt}" if label else txt)
        abstract = "\n".join(p for p in abstract_parts if p)

        # 期刊名称（全称 + 缩写，用于影响因子映射）
        journal = cls._text(article.find("Journal/Title"))
        journal_abbr = cls._text(article.find("Journal/ISOAbbreviation"))
        if not journal_abbr:
            journal_abbr = cls._text(medline.find("MedlineJournalInfo/MedlineTA"))

        # 发表年份
        pub_date = article.find("Journal/JournalIssue/PubDate")
        year = cls._text(pub_date.find("Year")) if pub_date is not None else ""
        if not year and pub_date is not None:
            medline_date = cls._text(pub_date.find("MedlineDate"))
            year = medline_date[:4] if medline_date else ""

        # 作者
        authors = []
        for a in article.findall(".//AuthorList/Author"):
            last = cls._text(a.find("LastName"))
            fore = cls._text(a.find("ForeName")) or cls._text(a.find("Initials"))
            name = f"{last} {fore}".strip()
            if name:
                authors.append(name)

        pub_types = [cls._text(p) for p in article.findall(".//PublicationTypeList/PublicationType")]
        mesh = [cls._text(m) for m in medline.findall(".//MeshHeadingList/MeshHeading/DescriptorName")]
        keywords = [cls._text(k) for k in medline.findall(".//KeywordList/Keyword")]

        # DOI
        doi = ""
        for aid in art.findall(".//PubmedData/ArticleIdList/ArticleId"):
            if aid.get("IdType") == "doi":
                doi = cls._text(aid)
                break

        pmid = cls._text(medline.find("PMID"))
        return {
            "pmid": pmid,
            "title": cls._text(article.find("ArticleTitle")),
            "abstract": abstract,
            "journal": journal,
            "journal_abbr": journal_abbr,
            "year": year,
            "authors": authors,
            "pub_types": pub_types,
            "mesh": mesh,
            "keywords": keywords,
            "doi": doi,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        }
