<template>
  <section>
    <!-- 首屏主视觉 -->
    <div v-if="!result" class="hero">
      <h2 class="hero-title">检索文献并生成计量与综述分析</h2>
      <p class="hero-sub">支持输入研究关键词，自动扩展检索式并抓取 PubMed 文献</p>
      <p class="hero-sub">多智能体协同完成统计可视化、研究热点词云、高影响力文献与智能综述</p>
    </div>

    <!-- 检索区 -->
    <form class="search-card" :class="{ compact: !!result }" @submit.prevent="run">
      <div class="search-line">
        <svg class="search-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <circle cx="11" cy="11" r="7" stroke="currentColor" stroke-width="2" />
          <path d="M20 20l-3.5-3.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
        </svg>
        <input
          v-model="keyword"
          class="search-input"
          placeholder="输入研究关键词，如：癌症免疫治疗 / cancer immunotherapy"
        />
      </div>
      <div class="search-actions">
        <label class="field">
          <span class="field-label">近 N 年</span>
          <input
            v-model.number="recentYears"
            class="field-input"
            type="number"
            min="1"
            max="10"
            step="1"
            placeholder="1-10年"
          />
        </label>
        <label class="field">
          <span class="field-label">解析篇数</span>
          <input
            v-model.number="maxFetch"
            class="field-input"
            type="number"
            min="10"
            max="500"
            step="10"
            placeholder="10-500篇"
          />
        </label>
        <button class="btn btn-primary" :disabled="loading || !canRun">
          {{ loading ? '分析中…' : '开始分析' }}
        </button>
      </div>
    </form>

    <!-- 能力卡片 -->
    <div v-if="!result" class="feature-cards">
      <div v-for="f in features" :key="f.label" class="feature-card">
        <div class="feature-label">{{ f.label }}</div>
        <div class="feature-desc">{{ f.desc }}</div>
      </div>
    </div>

    <p v-if="!result" class="data-note">
      数据来源：NCBI PubMed（E-utilities）+ JCR 影响因子与分区 + 中科院分区，综述由 DeepSeek 生成，仅供参考
    </p>

    <div v-if="error" class="error">{{ error }}</div>
    <div v-if="loading" class="loading">正在检索 PubMed 并生成分析结果，请稍候…</div>

    <AnalysisResult v-if="result && !loading" :result="result" />
  </section>
</template>

<script>
import { ref, computed } from 'vue'
import { runAnalysis } from '../api/entries.js'
import AnalysisResult from '../components/AnalysisResult.vue'

export default {
  name: 'AnalysisPage',
  components: { AnalysisResult },
  setup() {
    const keyword = ref('')
    const recentYears = ref(null)   // 留空则用后端默认值
    const maxFetch = ref(null)      // 留空则用后端默认值
    const loading = ref(false)
    const error = ref('')
    const result = ref(null)

    // 关键词必填；年份、解析篇数可留空（走默认），填写则需在合法范围内
    const canRun = computed(
      () =>
        !!keyword.value.trim() &&
        (recentYears.value == null || (recentYears.value >= 1 && recentYears.value <= 10)) &&
        (maxFetch.value == null || (maxFetch.value >= 10 && maxFetch.value <= 500))
    )

    const features = [
      { label: '检索', desc: 'PubMed 关键词检索' },
      { label: '统计', desc: '年份 · 分区 · IF 分布' },
      { label: '热点', desc: '关键词与 MeSH 词云' },
      { label: 'Top', desc: '高影响力文献 Top100' },
      { label: '综述', desc: 'DeepSeek 智能综述' },
    ]

    async function run() {
      const kw = keyword.value.trim()
      if (!kw) return
      loading.value = true
      error.value = ''
      try {
        const payload = { keyword: kw }
        if (recentYears.value != null) payload.recent_years = recentYears.value
        if (maxFetch.value != null) payload.max_fetch = maxFetch.value
        result.value = await runAnalysis(payload)
      } catch (e) {
        error.value = e.message
        result.value = null
      } finally {
        loading.value = false
      }
    }

    return { keyword, recentYears, maxFetch, loading, error, result, run, canRun, features }
  },
}
</script>

<style scoped>
.hero {
  text-align: center;
  padding: 28px 16px 20px;
}

.hero-title {
  font-size: 32px;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: #1a1a2e;
  line-height: 1.25;
}

.hero-sub {
  margin-top: 10px;
  font-size: 14px;
  color: #8a94a6;
  line-height: 1.7;
}

/* 检索卡片 */
.search-card {
  max-width: 860px;
  margin: 0 auto 24px;
  padding: 16px;
  background: #fff;
  border: 1px solid #e6e9ef;
  border-radius: 16px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
  transition: box-shadow 0.2s;
}

.search-card:focus-within {
  box-shadow: 0 12px 34px rgba(37, 99, 235, 0.12);
}

.search-line {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 8px;
  border-bottom: 1px solid #eef1f5;
}

.search-icon {
  width: 20px;
  height: 20px;
  color: #94a3b8;
  flex: none;
}

.search-input {
  flex: 1;
  border: none;
  outline: none;
  padding: 12px 0;
  font-size: 16px;
  color: #1a1a2e;
  background: transparent;
}

.search-input::placeholder {
  color: #b0b8c4;
}

.search-actions {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  padding: 14px 8px 2px;
  flex-wrap: wrap;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-size: 12px;
  color: #8a94a6;
}

.field-input {
  width: 120px;
  padding: 9px 12px;
  border: 1px solid #d0d0d0;
  border-radius: 10px;
  font-size: 14px;
  background: #fff;
}

.field-input:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.search-actions .btn-primary {
  margin-left: auto;
  padding: 11px 26px;
  border-radius: 10px;
  font-size: 15px;
}

/* 能力卡片 */
.feature-cards {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 14px;
  max-width: 860px;
  margin: 0 auto;
}

.feature-card {
  text-align: center;
  padding: 18px 10px;
  background: #fff;
  border: 1px solid #e6e9ef;
  border-radius: 14px;
  transition: transform 0.18s, box-shadow 0.18s, border-color 0.18s;
}

.feature-card:hover {
  transform: translateY(-3px);
  border-color: #c7d2fe;
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08);
}

.feature-label {
  font-size: 16px;
  font-weight: 700;
  color: #2563eb;
  letter-spacing: 0.01em;
}

.feature-desc {
  margin-top: 8px;
  font-size: 12px;
  color: #8a94a6;
  line-height: 1.5;
}

.data-note {
  max-width: 860px;
  margin: 22px auto 0;
  text-align: center;
  font-size: 12px;
  color: #a0a8b6;
  line-height: 1.8;
}

@media (max-width: 760px) {
  .hero-title { font-size: 24px; }
  .feature-cards { grid-template-columns: repeat(2, 1fr); }
  .feature-cards .feature-card:last-child { grid-column: 1 / -1; }
  .search-actions .btn-primary { margin-left: 0; width: 100%; }
}
</style>
