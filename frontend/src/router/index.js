import { createRouter, createWebHashHistory } from 'vue-router'
import AnalysisPage from '../views/AnalysisPage.vue'
import HistoryPage from '../views/HistoryPage.vue'

const routes = [
  { path: '/', name: 'analysis', component: AnalysisPage },
  { path: '/history', name: 'history', component: HistoryPage },
]

export default createRouter({
  history: createWebHashHistory(),
  routes,
})
