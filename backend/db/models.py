"""
Tortoise ORM 模型定义
"""
from tortoise import fields
from tortoise.models import Model


class QueryRun(Model):
    """一次用户询问（一次完整分析）"""

    query_id = fields.CharField(max_length=36, unique=True)   # 询问唯一标识
    keyword = fields.CharField(max_length=255)                # 用户原始关键词
    query_string = fields.TextField(null=True)                # 最终使用的 PubMed 检索式
    translated = fields.CharField(max_length=255, null=True)  # 关键词的英文翻译/扩展
    recent_years = fields.IntField(default=5)                 # “近 N 年”口径
    max_fetch = fields.IntField(default=100)                  # 本次最多解析文献数
    total_hits = fields.IntField(default=0)                   # PubMed 命中总数
    fetched = fields.IntField(default=0)                      # 实际解析（入库）文献数
    # ---- AI 生成结果 ----
    stats = fields.JSONField(default=dict)                    # 计量统计（年份/分区/影响因子等）
    wordcloud = fields.JSONField(default=list)                # 研究热点词云
    directions = fields.JSONField(default=list)               # 研究方向（主题词）
    direction_summary = fields.TextField(null=True)           # 研究方向概括
    top_papers = fields.JSONField(default=list)               # 影响力 Top 文献
    report = fields.JSONField(default=dict)                   # 中文综述报告

    create_time = fields.DatetimeField(auto_now_add=True)
    update_time = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "query_run"


class Article(Model):
    """文献元数据（含映射后的影响因子 / 分区），按 pmid 去重"""

    pmid = fields.CharField(max_length=32, pk=True)           # PubMed 唯一编号，主键即去重键
    title = fields.TextField(null=True)                       # 标题
    abstract = fields.TextField(null=True)                    # 摘要
    journal = fields.CharField(max_length=512, null=True)     # 期刊全称
    journal_abbr = fields.CharField(max_length=255, null=True)  # 期刊缩写
    year = fields.CharField(max_length=8, null=True)          # 发表年份
    authors = fields.JSONField(default=list)                  # 作者列表
    pub_types = fields.JSONField(default=list)                # 出版类型
    mesh = fields.JSONField(default=list)                     # MeSH 主题词
    keywords = fields.JSONField(default=list)                 # 作者关键词
    doi = fields.CharField(max_length=255, null=True)         # DOI
    url = fields.CharField(max_length=512, null=True)         # PubMed 原文链接
    impact_factor = fields.FloatField(null=True)              # 影响因子（来自 JCR）
    jcr_quartile = fields.CharField(max_length=16, null=True)  # JCR 分区 Q1-Q4
    sci_quartile = fields.CharField(max_length=16, null=True)  # 中科院分区 1-4 区
    create_time = fields.DatetimeField(auto_now_add=True)
    update_time = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "article"


class QueryArticle(Model):
    """询问-文献关联：记录某篇文献出现在哪次询问里"""

    query = fields.ForeignKeyField(
        "models.QueryRun", related_name="links", on_delete=fields.CASCADE
    )
    article = fields.ForeignKeyField(
        "models.Article", related_name="links", on_delete=fields.CASCADE
    )

    class Meta:
        table = "query_article"
        unique_together = (("query", "article"),)   # 同一次询问同一篇文献只记一次
