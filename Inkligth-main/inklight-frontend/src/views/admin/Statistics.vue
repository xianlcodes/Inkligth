<template>
  <div class="admin-page">
    <div class="section-bar">
      <div class="section-bar-line"></div>
      <h2 class="section-title">数据统计</h2>
      <span class="section-accent">STATISTICS</span>
    </div>

    <div class="mb-6">
      <el-radio-group v-model="period" @change="loadTimeseries">
        <el-radio-button value="day">近30天</el-radio-button>
        <el-radio-button value="week">近12周</el-radio-button>
        <el-radio-button value="month">近12月</el-radio-button>
        <el-radio-button value="year">近3年</el-radio-button>
      </el-radio-group>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon" style="background:#ecfeff;color:#0e7490"><el-icon :size="24"><UserFilled /></el-icon></div>
        <div class="stat-card-body">
          <p class="stat-value">{{ overview?.total_users ?? '-' }}</p>
          <p class="stat-label">用户总数</p>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background:var(--bg-secondary);color:var(--text-secondary)"><el-icon :size="24"><Document /></el-icon></div>
        <div class="stat-card-body">
          <p class="stat-value">{{ overview?.total_literatures ?? '-' }}</p>
          <p class="stat-label">文献总数</p>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background:#f0fdf4;color:#16a34a"><el-icon :size="24"><Checked /></el-icon></div>
        <div class="stat-card-body">
          <p class="stat-value">{{ overview?.total_read_literatures ?? '-' }}</p>
          <p class="stat-label">已读文献</p>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background:#fff7ed;color:#ea580c"><el-icon :size="24"><Clock /></el-icon></div>
        <div class="stat-card-body">
          <p class="stat-value">{{ overview?.total_unread_literatures ?? '-' }}</p>
          <p class="stat-label">未读文献</p>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background:#eff6ff;color:#2563eb"><el-icon :size="24"><Notebook /></el-icon></div>
        <div class="stat-card-body">
          <p class="stat-value">{{ overview?.total_notes ?? '-' }}</p>
          <p class="stat-label">笔记总数</p>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background:var(--bg-secondary);color:var(--text-secondary)"><el-icon :size="24"><DataAnalysis /></el-icon></div>
        <div class="stat-card-body">
          <p class="stat-value">{{ overview?.total_presentations ?? '-' }}</p>
          <p class="stat-label">组会总数</p>
        </div>
      </div>
    </div>

    <div class="chart-section" v-loading="chartLoading">
      <div class="px-6 pt-6 pb-4">
        <div class="flex items-center gap-3 mb-5">
          <div class="rounded-md flex items-center justify-center flex-shrink-0" style="width:36px;height:36px;background:linear-gradient(135deg,#ecfeff,#ccfbf1);color:#0d9488">
            <el-icon :size="18"><UserFilled /></el-icon>
          </div>
          <div class="flex flex-col gap-0_5">
            <h3 class="text-base font-semibold text-slate-800 m-0">新增用户趋势</h3>
            <span class="text-xs text-slate-400">用户增长情况统计</span>
          </div>
        </div>
        <div ref="userChartRef" class="w-full" style="height:280px"></div>
        <el-empty v-if="!tsData?.new_users?.length" description="暂无数据" :image-size="40" />
      </div>

      <div class="h-px mx-6" style="background:linear-gradient(to right,transparent,var(--border-color),transparent)"></div>

      <div class="px-6 pt-6 pb-4">
        <div class="flex items-center gap-3 mb-5">
          <div class="rounded-md flex items-center justify-center flex-shrink-0" style="width:36px;height:36px;background:linear-gradient(135deg,#eef2ff,#e0e7ff);color:#4f46e5">
            <el-icon :size="18"><Document /></el-icon>
          </div>
          <div class="flex flex-col gap-0_5">
            <h3 class="text-base font-semibold text-slate-800 m-0">新增文献趋势</h3>
            <span class="text-xs text-slate-400">文献入库情况统计</span>
          </div>
        </div>
        <div ref="litChartRef" class="w-full" style="height:280px"></div>
        <el-empty v-if="!tsData?.new_literatures?.length" description="暂无数据" :image-size="40" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import {
  UserFilled, Document, Checked, Clock, Notebook, DataAnalysis,
} from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { getStatsOverview, getStatsTimeseries, type StatsOverview, type TimeSeriesStats } from '@/api/admin'

const overview = ref<StatsOverview | null>(null)
const tsData = ref<TimeSeriesStats | null>(null)
const period = ref('day')
const chartLoading = ref(false)

const userChartRef = ref<HTMLDivElement | null>(null)
const litChartRef = ref<HTMLDivElement | null>(null)
let userChart: echarts.ECharts | null = null
let litChart: echarts.ECharts | null = null

function formatDate(dateStr: string): string {
  if (dateStr.length > 10) return dateStr.slice(5, 10)
  return dateStr
}

function makeLineOption(data: { date: string; value: number }[], color: string, areaColor: string) {
  return {
    grid: { left: 40, right: 20, top: 20, bottom: 30 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(30, 41, 59, 0.92)',
      borderColor: 'transparent',
      textStyle: { color: '#fff', fontSize: 13 },
      formatter: (params: { name: string; value: number }[]) => {
        const p = params[0]
        return `<div style="font-size:12px;color:#94a3b8;margin-bottom:4px">${p.name}</div>
          <div><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${color};margin-right:6px"></span>${p.value}</div>`
      },
    },
    xAxis: {
      type: 'category',
      data: data.map(d => formatDate(d.date)),
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisTick: { show: false },
      axisLabel: { color: '#94a3b8', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } },
      axisLabel: { color: '#94a3b8', fontSize: 11 },
    },
    series: [{
      type: 'line',
      data: data.map(d => d.value),
      smooth: 0.4,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: { color, width: 2.5 },
      itemStyle: {
        color,
        borderColor: '#fff',
        borderWidth: 2,
      },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: areaColor },
          { offset: 1, color: 'rgba(255,255,255,0)' },
        ]),
      },
    }],
    dataZoom: [
      {
        type: 'inside',
        start: 0,
        end: 100,
        zoomOnMouseWheel: true,
        moveOnMouseMove: true,
      },
    ],
  }
}

function initCharts() {
  if (userChartRef.value) {
    userChart = echarts.init(userChartRef.value)
  }
  if (litChartRef.value) {
    litChart = echarts.init(litChartRef.value)
  }
  renderCharts()
}

function renderCharts() {
  if (userChart && tsData.value?.new_users?.length) {
    userChart.setOption(makeLineOption(tsData.value.new_users, '#0d9488', 'rgba(13,148,136,0.15)'), true)
  }
  if (litChart && tsData.value?.new_literatures?.length) {
    litChart.setOption(makeLineOption(tsData.value.new_literatures, '#6366f1', 'rgba(99,102,241,0.12)'), true)
  }
}

function disposeCharts() {
  userChart?.dispose()
  litChart?.dispose()
  userChart = null
  litChart = null
}

async function loadOverview() {
  try {
    const res = await getStatsOverview()
    overview.value = res.data
  } catch { /* handled silently */ }
}

async function loadTimeseries() {
  chartLoading.value = true
  try {
    const res = await getStatsTimeseries(period.value)
    tsData.value = res.data
    await nextTick()
    if (!userChart && !litChart) {
      initCharts()
    } else {
      renderCharts()
    }
  } catch { /* handled silently */ }
  finally { chartLoading.value = false }
}

let resizeHandler: (() => void) | null = null

onMounted(() => {
  loadOverview()
  loadTimeseries()
  resizeHandler = () => {
    userChart?.resize()
    litChart?.resize()
  }
  window.addEventListener('resize', resizeHandler)
})

onUnmounted(() => {
  disposeCharts()
  if (resizeHandler) {
    window.removeEventListener('resize', resizeHandler)
  }
})
</script>

<style scoped>
.admin-page {
  max-width: 1200px;
}

/* ── Section Bar ── */
.section-bar {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 24px;
}

.section-bar-line {
  width: 4px;
  height: 22px;
  border-radius: 3px;
  background: linear-gradient(180deg, var(--accent-primary) 0%, var(--sky-400) 100%);
  flex-shrink: 0;
}

.section-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  letter-spacing: -0.01em;
}

.section-accent {
  margin-left: 4px;
  font-size: 10px;
  font-weight: 600;
  color: var(--sky-300);
  letter-spacing: 0.12em;
}

/* ── Stats Grid ── */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: rgba(255,255,255,0.55);
  backdrop-filter: blur(4px);
  border: 1px solid rgba(221,214,200,0.25);
  border-radius: var(--radius-lg);
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  transition: all 0.2s;
}

.stat-card:hover {
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}

.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-card-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  line-height: 1.2;
}

.stat-label {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0;
}

/* ── Chart Section ── */
.chart-section {
  background: rgba(255,255,255,0.5);
  backdrop-filter: blur(4px);
  border: 1px solid rgba(221,214,200,0.2);
  border-radius: var(--radius-xl);
  overflow: hidden;
}
</style>
