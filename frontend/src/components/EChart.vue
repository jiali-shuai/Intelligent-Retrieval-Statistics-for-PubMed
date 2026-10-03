<template>
  <div ref="el" class="echart" :style="{ height }"></div>
</template>

<script>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import 'echarts-wordcloud'

export default {
  name: 'EChart',
  props: {
    option: { type: Object, required: true },
    height: { type: String, default: '300px' },
  },
  setup(props) {
    const el = ref(null)
    let chart = null

    function render() {
      if (!el.value) return
      if (!chart) chart = echarts.init(el.value)
      chart.setOption(props.option, true)
    }

    function resize() {
      if (chart) chart.resize()
    }

    onMounted(() => {
      render()
      window.addEventListener('resize', resize)
    })

    onBeforeUnmount(() => {
      window.removeEventListener('resize', resize)
      if (chart) {
        chart.dispose()
        chart = null
      }
    })

    watch(() => props.option, () => nextTick(render), { deep: true })

    return { el }
  },
}
</script>

<style scoped>
.echart {
  width: 100%;
}
</style>
