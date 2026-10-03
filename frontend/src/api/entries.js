import axios from 'axios'

const http = axios.create({
  baseURL: '/api',
  timeout: 200000,
})

http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const msg = err.response?.data?.detail || err.message || '请求失败'
    return Promise.reject(new Error(msg))
  },
)

/** 一站式文献分析：关键词 -> 检索 -> 统计 / 词云 / 方向 / Top100 / 综述 */
export function runAnalysis(payload) {
  return http.post('/analysis/run', payload)
}

export function checkHealth() {
  return http.get('/health')
}

/** 历史询问列表（分页，按时间倒序） */
export function listRuns(params) {
  return http.get('/history/runs', { params })
}

/** 单次询问详情（含 AI 生成结果） */
export function getRun(queryId) {
  return http.get(`/history/runs/${queryId}`)
}
