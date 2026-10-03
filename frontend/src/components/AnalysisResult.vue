<template>
  <div class="analysis-result">
    <!-- 检索信息 -->
    <div class="panel">
      <div class="query-row">
        <span class="tag">检索词</span>
        <span class="query-kw">{{ result.keyword }}</span>
        <span class="tag">英文 / 扩展</span>
        <span class="query-kw">{{ result.query.translated }}</span>
        <span class="tag tag-ok">AI 扩展</span>
        <span class="query-time">生成于 {{ generatedAt }}</span>
      </div>
    </div>

    <!-- 概览卡片 -->
    <div class="stat-cards">
      <div class="stat-card" v-for="c in statCards" :key="c.label">
        <div class="stat-value">{{ c.value }}</div>
        <div class="stat-label">{{ c.label }}</div>
      </div>
    </div>

    <!-- 图表区 -->
    <div class="chart-grid">
      <div class="panel chart-wide">
        <h3>文献年份分布</h3>
        <EChart :option="yearOption" height="280px" />
      </div>
      <div class="panel">
        <h3>JCR 分区分布（Q1-Q4）</h3>
        <EChart :option="jcrQuartileOption" height="280px" />
      </div>
      <div class="panel">
        <h3>中科院分区分布（1-4 区）</h3>
        <EChart :option="casQuartileOption" height="280px" />
      </div>
      <div class="panel">
        <h3>影响因子分布</h3>
        <EChart :option="ifOption" height="280px" />
      </div>
      <div class="panel">
        <h3>高产期刊 Top15</h3>
        <EChart :option="journalOption" height="420px" />
      </div>
    </div>

    <!-- 词云 -->
    <div class="panel">
      <h3>研究热点词云</h3>
      <EChart :option="cloudOption" height="420px" />
    </div>

    <!-- 研究方向 -->
    <div class="panel">
      <h3>研究方向总结</h3>
      <p class="summary-text">{{ result.direction_summary }}</p>
      <div class="direction-tags">
        <span class="dir-tag" v-for="d in result.directions" :key="d.name">
          {{ d.name }} <b>{{ d.count }}</b>
        </span>
      </div>
    </div>

    <!-- Top 文献 -->
    <div class="panel">
      <h3>
        影响力 Top 文献（近 {{ result.stats.recent_years }} 年，共 {{ result.top_papers.length }} 篇）
      </h3>
      <div class="table-wrap">
        <table class="entry-table paper-table">
          <thead>
            <tr>
              <th class="col-rank">#</th>
              <th>标题 / 期刊</th>
              <th class="col-if">影响因子</th>
              <th class="col-q">JCR 分区</th>
              <th class="col-q">中科院分区</th>
              <th class="col-year">年份</th>
              <th class="col-link">链接</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in result.top_papers" :key="p.pmid">
              <td class="col-rank">{{ p.rank }}</td>
              <td>
                <div class="paper-title">{{ p.title }}</div>
                <div class="paper-meta">
                  {{ p.journal }} · {{ (p.authors || []).join(', ') }}{{
                    p.author_count > (p.authors || []).length ? ' 等' : ''
                  }}
                </div>
              </td>
              <td class="col-if">{{ p.impact_factor ?? '—' }}</td>
              <td class="col-q">
                <span class="q-badge" :class="qClass(p.jcr_quartile)">{{ p.jcr_quartile }}</span>
              </td>
              <td class="col-q">
                <span class="q-badge" :class="qClass(p.sci_quartile)">{{ p.sci_quartile }}</span>
              </td>
              <td class="col-year">{{ p.year }}</td>
              <td class="col-link">
                <a :href="p.url" target="_blank" rel="noopener">PubMed</a>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 综述报告 -->
    <div class="panel">
      <h3>
        领域综述报告
        <span class="tag tag-ok">AI 生成</span>
      </h3>
      <ol class="report-list">
        <li v-for="(b, i) in reportBullets" :key="i">
          <div class="report-title">{{ b.title }}</div>
          <div class="report-content">{{ b.content }}</div>
        </li>
      </ol>
    </div>
  </div>
</template>

<script>
import { computed } from 'vue'
import EChart from './EChart.vue'

const PALETTE = [
  '#2563eb', '#7c3aed', '#0ea5e9', '#10b981', '#f59e0b',
  '#ef4444', '#ec4899', '#14b8a6', '#6366f1', '#84cc16',
]

function randomColor() {
  return PALETTE[Math.floor(Math.random() * PALETTE.length)]
}

// 分区徽标配色：JCR 分区（Q1-Q4）与中科院分区（1-4 区）
const QUARTILE_CLASS = {
  Q1: 'q1', Q2: 'q2', Q3: 'q3', Q4: 'q4',
  '1区': 'q1', '2区': 'q2', '3区': 'q3', '4区': 'q4',
}

export default {
  name: 'AnalysisResult',
  components: { EChart },
  props: {
    // 分析结果对象（与 /api/analysis/run 返回结构一致）
    result: { type: Object, required: true },
  },
  setup(props) {
    const generatedAt = computed(() =>
      String(props.result.generated_at || '').replace('T', ' ')
    )

    const statCards = computed(() => {
      const s = props.result?.stats
      if (!s) return []
      return [
        { label: `近 ${s.recent_years} 年命中总数`, value: s.total_hits },
        { label: '本次解析文献', value: s.fetched },
        { label: '高影响力文献', value: props.result?.top_papers?.length ?? 0 },
        { label: '平均影响因子', value: s.avg_if ?? '—' },
        { label: '最高影响因子', value: s.max_if ?? '—' },
        { label: '影响因子覆盖率', value: s.if_coverage + '%' },
      ]
    })

    const yearOption = computed(() => {
      const d = props.result?.stats?.by_year || []
      return {
        grid: { left: 45, right: 20, top: 30, bottom: 30 },
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: d.map((x) => x.year), boundaryGap: false },
        yAxis: { type: 'value', minInterval: 1 },
        series: [
          {
            type: 'line',
            smooth: true,
            symbolSize: 7,
            areaStyle: { opacity: 0.15 },
            itemStyle: { color: '#2563eb' },
            lineStyle: { color: '#2563eb', width: 2 },
            data: d.map((x) => x.count),
          },
        ],
      }
    })

    // 分区饼图：JCR 分区与中科院分区分别渲染
    function pieOption(data) {
      return {
        tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
        legend: { bottom: 0 },
        color: ['#ef4444', '#f59e0b', '#10b981', '#6b7280', '#94a3b8'],
        series: [
          {
            type: 'pie',
            radius: ['42%', '66%'],
            center: ['50%', '44%'],
            label: { formatter: '{b}\n{c} ({d}%)', fontSize: 12 },
            data: (data || []).map((x) => ({ name: x.name, value: x.value })),
          },
        ],
      }
    }

    const jcrQuartileOption = computed(() => pieOption(props.result?.stats?.by_jcr_quartile))
    const casQuartileOption = computed(() => pieOption(props.result?.stats?.by_sci_quartile))

    const ifOption = computed(() => {
      const d = props.result?.stats?.if_distribution || []
      return {
        grid: { left: 45, right: 20, top: 30, bottom: 30 },
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: d.map((x) => x.name) },
        yAxis: { type: 'value', minInterval: 1 },
        series: [
          {
            type: 'bar',
            barWidth: '52%',
            itemStyle: { color: '#7c3aed', borderRadius: [4, 4, 0, 0] },
            data: d.map((x) => x.value),
          },
        ],
      }
    })

    const journalOption = computed(() => {
      const d = (props.result?.stats?.by_journal || []).slice().reverse()
      return {
        grid: { left: 170, right: 30, top: 20, bottom: 30 },
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'value', minInterval: 1 },
        yAxis: {
          type: 'category',
          data: d.map((x) => x.name),
          axisLabel: { width: 160, overflow: 'truncate', fontSize: 11 },
        },
        series: [
          {
            type: 'bar',
            barWidth: '58%',
            itemStyle: { color: '#0ea5e9', borderRadius: [0, 4, 4, 0] },
            data: d.map((x) => x.count),
          },
        ],
      }
    })

    const cloudOption = computed(() => {
      const d = props.result?.wordcloud || []
      return {
        tooltip: {},
        series: [
          {
            type: 'wordCloud',
            shape: 'circle',
            left: 'center',
            top: 'center',
            width: '96%',
            height: '96%',
            sizeRange: [14, 56],
            rotationRange: [-45, 45],
            rotationStep: 15,
            gridSize: 8,
            drawOutOfBound: false,
            textStyle: { color: () => randomColor(), fontWeight: 'bold' },
            emphasis: { textStyle: { shadowBlur: 8, shadowColor: '#333' } },
            data: d.map((w) => ({ name: w.word, value: w.weight })),
          },
        ],
      }
    })

    const reportBullets = computed(() => props.result?.report?.bullets || [])

    function qClass(q) {
      return QUARTILE_CLASS[q] || 'qx'
    }

    return {
      generatedAt, statCards, yearOption, jcrQuartileOption, casQuartileOption,
      ifOption, journalOption, cloudOption, reportBullets, qClass,
    }
  },
}
</script>

<style scoped>
.panel {
  background: #fff;
  border-radius: 10px;
  padding: 18px 20px;
  margin-bottom: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

.panel h3 {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.query-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  font-size: 13px;
}

.query-kw { color: #1a1a2e; font-weight: 500; }
.query-time { margin-left: auto; color: #9aa3b2; font-size: 12px; }

.tag {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 10px;
  font-size: 11px;
  background: #eef2ff;
  color: #4338ca;
}

.tag-ok { background: #dcfce7; color: #15803d; }

.stat-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 14px;
  margin-bottom: 20px;
}

.stat-card {
  background: #fff;
  border-radius: 10px;
  padding: 18px;
  text-align: center;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #2563eb;
  line-height: 1.3;
}

.stat-label {
  margin-top: 6px;
  font-size: 12px;
  color: #8a94a6;
}

.chart-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.chart-grid .panel { margin-bottom: 0; }

/* 年份分布占满整行；两个分区图并排 */
.chart-wide { grid-column: 1 / -1; }

@media (max-width: 760px) {
  .chart-grid { grid-template-columns: 1fr; }
}

.summary-text {
  font-size: 14px;
  line-height: 1.8;
  color: #374151;
  margin-bottom: 14px;
}

.direction-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.dir-tag {
  padding: 5px 12px;
  border-radius: 16px;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 13px;
}

.dir-tag b { color: #1e40af; margin-left: 2px; }

.table-wrap {
  max-height: 560px;
  overflow-y: auto;
  border: 1px solid #eef0f3;
  border-radius: 8px;
}

.paper-table { border-radius: 8px; }

.entry-table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
}

.entry-table th, .entry-table td {
  padding: 12px 16px;
  text-align: left;
  font-size: 14px;
  border-bottom: 1px solid #eee;
  vertical-align: top;
}

.entry-table th {
  background: #f9fafb;
  font-weight: 600;
  color: #555;
  position: sticky;
  top: 0;
  z-index: 1;
}

.entry-table tbody tr:hover { background: #f8faff; }

.col-rank { width: 44px; color: #94a3b8; text-align: center; }
.col-if { width: 90px; text-align: center; color: #7c3aed; font-weight: 600; }
.col-q { width: 70px; text-align: center; }
.col-year { width: 64px; text-align: center; color: #64748b; }
.col-link { width: 80px; text-align: center; }

.paper-title {
  font-size: 13px;
  color: #1a1a2e;
  line-height: 1.5;
  font-weight: 500;
}

.paper-meta {
  margin-top: 4px;
  font-size: 12px;
  color: #94a3b8;
  line-height: 1.5;
}

.paper-table a { color: #2563eb; text-decoration: none; font-size: 12px; }
.paper-table a:hover { text-decoration: underline; }

.q-badge {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 10px;
  font-size: 12px;
}

.q-badge.q1 { background: #fee2e2; color: #b91c1c; }
.q-badge.q2 { background: #ffedd5; color: #c2410c; }
.q-badge.q3 { background: #dcfce7; color: #15803d; }
.q-badge.q4 { background: #e0e7ff; color: #4338ca; }
.q-badge.qx { background: #f1f5f9; color: #64748b; }

.report-list {
  margin: 0;
  padding-left: 4px;
  list-style: none;
}

.report-list li {
  padding: 12px 0;
  border-bottom: 1px dashed #eef0f3;
}

.report-list li:last-child { border-bottom: none; }

.report-title {
  font-size: 14px;
  font-weight: 600;
  color: #1d4ed8;
  margin-bottom: 6px;
}

.report-content {
  font-size: 14px;
  line-height: 1.9;
  color: #374151;
}
</style>
