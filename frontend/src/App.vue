<template>
  <div id="app-container">
    <header class="app-header">
      <div class="brand">
        <div class="logo" aria-hidden="true">PM</div>
        <div class="brand-text">
          <h1>PubMed 文献计量与综述分析</h1>
          <p class="subtitle">关键词检索 · 统计可视化 · 研究热点词云 · 高影响力文献 · 智能综述</p>
        </div>
      </div>
      <div class="header-status">
        <span :class="['status-dot', apiOnline ? 'online' : 'offline']"></span>
        {{ apiOnline ? '服务在线' : '服务离线' }}
      </div>
    </header>

    <nav class="app-nav">
      <router-link to="/" class="nav-link">文献分析</router-link>
      <router-link to="/history" class="nav-link">历史记录</router-link>
    </nav>

    <main class="app-main">
      <div v-if="!apiOnline && !loading" class="error">
        无法连接到后端服务，请确认后端已启动（端口 8000）
      </div>
      <router-view v-else />
    </main>

    <footer class="app-footer">
      <details>
        <summary>设计说明与思考</summary>
        <ul>
          <li>
            <b>多智能体编排：</b>由「总管 agent」依据共享状态统一调度 3 名成员 agent——
            检索策略员（提取关键词、构建检索式并执行检索）、统计员（计量统计 + 生成词云与研究方向）、
            综述撰写员（筛选 Top N 并撰写中文综述）；总管是唯一决策中枢，成员之间不直接通信，
            并在样本不足时决定放宽检索式重试。
          </li>
          <li>
            <b>数据源：</b>基于 NCBI E-utilities 检索真实 PubMed 文献，按“近 N 年”发表年份限定，
            解析标题、摘要、作者、期刊与 MeSH 主题词，供下游统计与综述使用。
          </li>
          <li>
            <b>影响因子 / 分区：</b>PubMed 本身不提供 IF 与分区，本 demo 使用两份数据文件
            （JCR.xlsx 提供影响因子与 JCR 分区 Q1-Q4，SCI.xlsx 提供中科院分区 1-4 区），
            按“期刊全称 / 缩写”归一化匹配，两类分区各自独立统计、分别展示。
          </li>
          <li>
            <b>大模型：</b>DeepSeek 负责关键词翻译扩展、词云与研究方向提取（阅读论文标题/关键词/主题词后生成）、
            方向概括与约 500 字中文综述。
          </li>
          <li>
            <b>可视化选型：</b>前端一次请求拿到全部分析结果，使用 ECharts 统一渲染年份 / 分区 / IF 分布与关键词词云，减少网络往返。
          </li>
        </ul>
      </details>
    </footer>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { checkHealth } from './api/entries.js'

export default {
  name: 'App',
  setup() {
    const apiOnline = ref(false)
    const loading = ref(true)

    onMounted(async () => {
      try {
        await checkHealth()
        apiOnline.value = true
      } catch {
        apiOnline.value = false
      } finally {
        loading.value = false
      }
    })

    return { apiOnline, loading }
  },
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background: #f5f7fa;
  color: #333;
  min-height: 100vh;
}

#app-container {
  max-width: 1120px;
  margin: 0 auto;
  padding: 24px 16px 48px;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 20px;
  border-bottom: 1px solid #e0e0e0;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo {
  width: 44px;
  height: 44px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: #2563eb;
  color: #fff;
  font-size: 15px;
  font-weight: 800;
  letter-spacing: 0.04em;
}

.app-header h1 {
  font-size: 22px;
  font-weight: 700;
  color: #1a1a2e;
}

.subtitle {
  margin-top: 6px;
  font-size: 13px;
  color: #8a94a6;
}

.header-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #666;
  white-space: nowrap;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot.online { background: #22c55e; }
.status-dot.offline { background: #ef4444; }

.app-nav {
  display: flex;
  gap: 20px;
  margin-top: 16px;
  border-bottom: 1px solid #e0e0e0;
}

.nav-link {
  padding: 8px 2px;
  font-size: 14px;
  color: #64748b;
  text-decoration: none;
  border-bottom: 2px solid transparent;
  transition: color 0.15s, border-color 0.15s;
}

.nav-link:hover { color: #1a1a2e; }

.nav-link.router-link-exact-active {
  color: #2563eb;
  border-bottom-color: #2563eb;
  font-weight: 600;
}

.app-main { padding-top: 24px; }

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.section-header h2 {
  font-size: 18px;
  font-weight: 600;
}

.btn {
  padding: 8px 18px;
  border: 1px solid #d0d0d0;
  border-radius: 6px;
  background: #fff;
  color: #333;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.15s;
}

.btn:hover { border-color: #999; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-primary {
  background: #2563eb;
  color: #fff;
  border-color: #2563eb;
}

.btn-primary:hover {
  background: #1d4ed8;
  border-color: #1d4ed8;
}

.loading, .empty, .error {
  text-align: center;
  padding: 48px 0;
  color: #999;
  font-size: 14px;
}

.error { color: #ef4444; }

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

.app-footer {
  margin-top: 32px;
  padding-top: 16px;
  border-top: 1px solid #e0e0e0;
  font-size: 13px;
  color: #666;
}

.app-footer summary {
  cursor: pointer;
  font-weight: 600;
  color: #2563eb;
  outline: none;
}

.app-footer ul {
  margin: 12px 0 0 20px;
  line-height: 1.9;
}

.app-footer code {
  background: #eef2ff;
  color: #4338ca;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 12px;
}
</style>
