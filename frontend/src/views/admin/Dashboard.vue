<script setup>
/** 仪表盘：汇总指标卡 + ECharts 按日趋势（访问/问答/token/耗时），30s 自动刷新 */
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import * as echarts from 'echarts'
import { adminApi } from '../../api'
import { useAdminStore } from '../../stores/admin'

const { t, locale } = useI18n()
const admin = useAdminStore()
const days = ref(7)
const summary = ref(null)
const daily = ref([])
const loading = ref(false)
let chart, timer

// 极简线性图标 (stroke path, 24 viewBox)
const ICONS = {
  eye: 'M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0z',
  chat: 'M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z',
  zap: 'M13 2 3 14h9l-1 8 10-12h-9l1-8z',
  clock: 'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z M12 6v6l4 2',
  layers: 'M12 2 2 7l10 5 10-5-10-5z M2 17l10 5 10-5 M2 12l10 5 10-5',
  file: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z M14 2v6h6 M16 13H8 M16 17H8',
}

const cards = [
  { key: 'pv', labelKey: 'pv', icon: 'eye', color: '#00594a' },
  { key: 'chat_count', labelKey: 'chatCount', icon: 'chat', color: '#b08a3e' },
  { key: 'total_tokens', labelKey: 'tokenUsage', icon: 'zap', color: '#2f6f8f' },
  { key: 'avg_chat_ms', labelKey: 'avgResponse', icon: 'clock', color: '#8e6fa8', ms: true },
  { key: 'session_count', labelKey: 'sessionCount', icon: 'layers', color: '#3e8e6c' },
  { key: 'document_count', labelKey: 'docCount', icon: 'file', color: '#b06c49' },
]

function fmtMs(v) {
  return v >= 1000 ? (v / 1000).toFixed(1) + ' s' : v + ' ms'
}
function fmtNum(v) {
  if (v == null) return '-'
  if (v >= 10000) return (v / 10000).toFixed(1) + 'w'
  if (v >= 1000) return (v / 1000).toFixed(1) + 'k'
  return String(v)
}

async function load() {
  loading.value = true
  try {
    const res = await adminApi.stats(days.value, admin.token)
    summary.value = res.summary
    daily.value = res.daily
    renderChart()
  } finally {
    loading.value = false
  }
}

function renderChart() {
  const el = document.getElementById('trend-chart')
  if (!el) return
  if (!chart) chart = echarts.init(el)
  const x = daily.value.map((d) => d.date.slice(5))
  const option = {
    color: ['#00594a', '#c8a565', '#2f6f8f'],
    tooltip: { trigger: 'axis' },
    legend: {
      data: [t('dashboard.seriesPv'), t('dashboard.seriesChat'), t('dashboard.seriesToken')],
      top: 0,
    },
    grid: { left: 50, right: 56, top: 36, bottom: 30 },
    xAxis: { type: 'category', data: x, axisLine: { lineStyle: { color: '#c7d4d0' } } },
    yAxis: [
      { type: 'value', name: t('dashboard.yCount'), splitLine: { lineStyle: { color: '#eef3f1' } } },
      { type: 'value', name: 'token', splitLine: { show: false } },
    ],
    series: [
      {
        name: t('dashboard.seriesPv'), type: 'bar', barMaxWidth: 26,
        itemStyle: { borderRadius: [5, 5, 0, 0], color: '#0a7a63' },
        data: daily.value.map((d) => d.pv),
      },
      {
        name: t('dashboard.seriesChat'), type: 'bar', barMaxWidth: 26,
        itemStyle: { borderRadius: [5, 5, 0, 0], color: '#c8a565' },
        data: daily.value.map((d) => d.chat_count),
      },
      {
        name: t('dashboard.seriesToken'), type: 'line', yAxisIndex: 1,
        smooth: true, symbolSize: 6,
        lineStyle: { width: 2.5 },
        data: daily.value.map((d) => d.prompt_tokens + d.completion_tokens),
      },
    ],
  }
  chart.setOption(option, true)
}

// 语言切换时重渲染图表文案
watch(() => locale.value, () => renderChart())

onMounted(() => {
  load()
  timer = setInterval(load, 30000)
  window.addEventListener('resize', renderChart)
})
onBeforeUnmount(() => {
  clearInterval(timer)
  window.removeEventListener('resize', renderChart)
  chart?.dispose()
})
</script>

<template>
  <div class="dashboard">
    <div class="head">
      <h2>{{ t('dashboard.title') }}</h2>
      <div class="range">
        <button :class="{ on: days === 7 }" @click="days = 7; load()">{{ t('dashboard.last7') }}</button>
        <button :class="{ on: days === 30 }" @click="days = 30; load()">{{ t('dashboard.last30') }}</button>
        <span class="refresh-tip">{{ t('dashboard.autoRefresh') }}</span>
      </div>
    </div>

    <div class="cards">
      <div v-for="c in cards" :key="c.key" class="card">
        <div class="icon" :style="{ background: c.color + '14', color: c.color }">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
            <path :d="ICONS[c.icon]" />
          </svg>
        </div>
        <div class="meta">
          <div class="num">
            {{ c.ms ? fmtMs(summary?.[c.key] ?? 0) : fmtNum(summary?.[c.key]) }}
          </div>
          <div class="label">{{ t('dashboard.' + c.labelKey) }}</div>
        </div>
      </div>
    </div>

    <div class="chart-card">
      <div class="chart-title">{{ t('dashboard.trend') }}</div>
      <div id="trend-chart" class="chart"></div>
    </div>

    <div class="sub-grid">
      <div class="info-card">
        <div class="t">{{ t('dashboard.tokenDetail') }}</div>
        <div class="row"><span>{{ t('dashboard.promptTokens') }}</span><b>{{ (summary?.prompt_tokens ?? 0).toLocaleString() }}</b></div>
        <div class="row"><span>{{ t('dashboard.completionTokens') }}</span><b>{{ (summary?.completion_tokens ?? 0).toLocaleString() }}</b></div>
        <div class="row"><span>{{ t('dashboard.totalTokens') }}</span><b>{{ (summary?.total_tokens ?? 0).toLocaleString() }}</b></div>
      </div>
      <div class="info-card">
        <div class="t">{{ t('dashboard.kbScale') }}</div>
        <div class="row"><span>{{ t('dashboard.doneDocs') }}</span><b>{{ summary?.document_count ?? '-' }}</b></div>
        <div class="row"><span>{{ t('dashboard.chunks') }}</span><b>{{ summary?.chunk_count ?? '-' }}</b></div>
        <div class="row"><span>{{ t('dashboard.sessions') }}</span><b>{{ summary?.session_count ?? '-' }}</b></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dashboard { max-width: 1200px; margin: 0 auto; }
.head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 18px; }
h2 { margin: 0; font-size: 20px; color: var(--c-text); }
.range { display: flex; align-items: center; gap: 8px; }
.range button {
  height: 30px; padding: 0 14px;
  border-radius: 999px; border: 1px solid var(--c-border);
  background: #fff; color: var(--c-text-2);
  font-size: 12.5px; cursor: pointer;
}
.range button.on { background: var(--c-primary); border-color: var(--c-primary); color: #fff; }
.refresh-tip { font-size: 11.5px; color: var(--c-text-3); margin-left: 6px; }

.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}
.card {
  background: var(--c-card);
  border: 1px solid var(--c-border);
  border-radius: var(--r-md);
  padding: 16px;
  display: flex; align-items: center; gap: 12px;
  box-shadow: var(--shadow-card);
}
.icon {
  width: 42px; height: 42px;
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.icon svg { width: 21px; height: 21px; }
.num { font-size: 21px; font-weight: 700; color: var(--c-text); line-height: 1.2; }
.label { font-size: 12px; color: var(--c-text-2); margin-top: 3px; }

.chart-card {
  background: var(--c-card);
  border: 1px solid var(--c-border);
  border-radius: var(--r-md);
  box-shadow: var(--shadow-card);
  padding: 18px;
  margin-bottom: 18px;
}
.chart-title { font-size: 14.5px; font-weight: 600; margin-bottom: 6px; color: var(--c-text); }
.chart { height: 340px; }

.sub-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.info-card {
  background: var(--c-card);
  border: 1px solid var(--c-border);
  border-radius: var(--r-md);
  box-shadow: var(--shadow-card);
  padding: 16px 18px;
}
.info-card .t { font-size: 14px; font-weight: 600; margin-bottom: 10px; color: var(--c-text); }
.row {
  display: flex; justify-content: space-between;
  font-size: 13px; color: var(--c-text-2);
  padding: 6px 0;
  border-bottom: 1px dashed var(--c-border);
}
.row:last-child { border-bottom: none; }
.row b { color: var(--c-primary); }
</style>
