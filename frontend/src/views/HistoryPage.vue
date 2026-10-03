<template>
  <section>
    <div class="section-header">
      <h2>历史记录</h2>
      <button class="btn" :disabled="loading" @click="load">刷新</button>
    </div>

    <div v-if="error" class="error">{{ error }}</div>
    <div v-if="loading" class="loading">正在加载历史记录…</div>
    <div v-else-if="!items.length" class="empty">暂无历史记录</div>

    <template v-else>
      <div class="panel">
        <div class="table-wrap">
          <table class="entry-table">
            <thead>
              <tr>
                <th class="col-time">时间</th>
                <th>关键词</th>
                <th class="col-num">近 N 年</th>
                <th class="col-num">命中</th>
                <th class="col-num">解析</th>
                <th class="col-op">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in items" :key="r.query_id">
                <td class="col-time">{{ r.create_time.replace('T', ' ').slice(0, 19) }}</td>
                <td>
                  <div class="kw">{{ r.keyword }}</div>
                  <div class="kw-sub" v-if="r.translated">{{ r.translated }}</div>
                </td>
                <td class="col-num">{{ r.recent_years }}</td>
                <td class="col-num">{{ r.total_hits }}</td>
                <td class="col-num">{{ r.fetched }}</td>
                <td class="col-op">
                  <button class="btn btn-sm" :disabled="detailLoading" @click="open(r)">
                    查看
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="pager">
        <button class="btn" :disabled="offset <= 0" @click="prev">上一页</button>
        <span class="pager-info">共 {{ total }} 条 · 第 {{ page }} / {{ pageCount }} 页</span>
        <button class="btn" :disabled="offset + limit >= total" @click="next">下一页</button>
      </div>
    </template>

    <!-- 详情：完整复现当时的分析页 -->
    <div v-if="detail" class="detail-mask" @click.self="detail = null">
      <div class="detail-panel">
        <div class="detail-head">
          <div class="detail-title">
            <h3>历史分析详情</h3>
            <span class="detail-sub">{{ detail.keyword }} · {{ formatTime(detail.create_time) }}</span>
          </div>
          <button class="btn btn-sm" @click="detail = null">关闭</button>
        </div>
        <div class="detail-body">
          <AnalysisResult :result="detailResult" />
        </div>
      </div>
    </div>
  </section>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { listRuns, getRun } from '../api/entries.js'
import AnalysisResult from '../components/AnalysisResult.vue'

export default {
  name: 'HistoryPage',
  components: { AnalysisResult },
  setup() {
    const items = ref([])
    const total = ref(0)
    const limit = ref(20)
    const offset = ref(0)
    const loading = ref(false)
    const error = ref('')

    const detail = ref(null)
    const detailLoading = ref(false)

    const page = computed(() => Math.floor(offset.value / limit.value) + 1)
    const pageCount = computed(() => Math.max(1, Math.ceil(total.value / limit.value)))

    // 把历史记录映射成与分析页一致的结果结构，交给共享组件渲染
    const detailResult = computed(() => {
      const d = detail.value
      if (!d) return null
      return {
        keyword: d.keyword,
        query: { translated: d.translated },
        generated_at: d.create_time,
        stats: d.stats || {},
        wordcloud: d.wordcloud || [],
        directions: d.directions || [],
        direction_summary: d.direction_summary || '',
        top_papers: d.top_papers || [],
        report: d.report || {},
      }
    })

    function formatTime(t) {
      return String(t || '').replace('T', ' ').slice(0, 19)
    }

    async function load() {
      loading.value = true
      error.value = ''
      try {
        const data = await listRuns({ limit: limit.value, offset: offset.value })
        items.value = data.items || []
        total.value = data.total || 0
      } catch (e) {
        error.value = e.message
        items.value = []
      } finally {
        loading.value = false
      }
    }

    async function open(r) {
      detailLoading.value = true
      error.value = ''
      try {
        detail.value = await getRun(r.query_id)
      } catch (e) {
        error.value = e.message
      } finally {
        detailLoading.value = false
      }
    }

    function prev() {
      offset.value = Math.max(0, offset.value - limit.value)
      load()
    }

    function next() {
      offset.value += limit.value
      load()
    }

    onMounted(load)

    return {
      items, total, limit, offset, loading, error,
      page, pageCount, load, prev, next,
      detail, detailLoading, open, detailResult, formatTime,
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

.table-wrap { overflow-x: auto; }

.col-time { width: 170px; white-space: nowrap; color: #64748b; }
.col-num { width: 80px; text-align: center; }
.col-op { width: 80px; text-align: center; }
.col-rank { width: 50px; text-align: center; }
.col-if { width: 100px; text-align: center; }
.col-year { width: 70px; text-align: center; }

.kw { color: #1a1a2e; font-weight: 500; }
.kw-sub { margin-top: 4px; font-size: 12px; color: #8a94a6; }

.btn-sm { padding: 4px 12px; font-size: 13px; }

.pager {
  display: flex;
  align-items: center;
  gap: 14px;
  justify-content: center;
}

.pager-info { font-size: 13px; color: #666; }

/* 详情弹层 */
.detail-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 40px 16px;
  overflow-y: auto;
  z-index: 50;
}

.detail-panel {
  background: #f5f7fa;
  border-radius: 12px;
  width: 100%;
  max-width: 1120px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

.detail-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #e0e0e0;
  background: #fff;
  border-radius: 12px 12px 0 0;
}

.detail-title { display: flex; align-items: baseline; gap: 12px; }
.detail-head h3 { font-size: 16px; font-weight: 600; }
.detail-sub { font-size: 12px; color: #8a94a6; }

.detail-body { padding: 20px; }
</style>
