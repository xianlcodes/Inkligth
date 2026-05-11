<template>
  <div class="reading-calendar">
    <div class="page-header">
      <div>
        <h1 class="page-title">阅读日历</h1>
        <p class="page-subtitle">追踪您的每日阅读习惯</p>
      </div>
      <el-button @click="router.push('/literature')" text>
        <el-icon><ArrowLeft /></el-icon>
        返回文献库
      </el-button>
    </div>

    <div class="calendar-summary" v-if="summary">
      <div class="summary-card">
        <span class="summary-label">近 {{ days }} 天总阅读</span>
        <span class="summary-value">{{ summary.total_pages }} 页</span>
      </div>
      <div class="summary-card">
        <span class="summary-label">活跃天数</span>
        <span class="summary-value">{{ summary.active_days }} 天</span>
      </div>
      <div class="summary-card">
        <span class="summary-label">总阅读时长</span>
        <span class="summary-value">{{ formatMinutes(summary.total_time) }} 分钟</span>
      </div>
    </div>

    <div class="heatmap-container" v-loading="loading">
      <div class="heatmap-legend">
        <span class="legend-label">少</span>
        <div
          v-for="level in 5"
          :key="level"
          class="legend-cell"
          :style="{ background: getHeatColor((level - 1) * 25) }"
        ></div>
        <span class="legend-label">多</span>
      </div>

      <div class="heatmap-grid">
        <div class="heatmap-months">
          <span
            v-for="(label, idx) in monthLabels"
            :key="idx"
            class="month-label"
            :style="{ gridColumn: label.col + ' / span ' + label.span }"
          >{{ label.name }}</span>
        </div>
        <div class="heatmap-body">
          <div class="heatmap-weekdays">
            <span>一</span>
            <span>三</span>
            <span>五</span>
          </div>
          <div class="heatmap-cells">
            <div
              v-for="(day, idx) in calendarDays"
              :key="idx"
              class="heatmap-cell"
              :style="{ background: getHeatColor(day.pages_read) }"
              :title="`${day.date}: ${day.pages_read} 页`"
            >
              <el-tooltip placement="top" :show-after="200">
                <template #content>
                  <div class="cell-tooltip">
                    <div>{{ formatDate(day.date) }}</div>
                    <div>{{ day.pages_read }} 页 · {{ formatMinutes(day.time_seconds) }} 分钟</div>
                  </div>
                </template>
                <span class="cell-inner"></span>
              </el-tooltip>
            </div>
          </div>
        </div>
      </div>
    </div>

    <el-empty v-if="!loading && calendarDays.length === 0" description="暂无阅读记录，去阅读文献吧" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { getCalendar, type CalendarDay } from '@/api/stats'

const router = useRouter()
const loading = ref(true)
const days = ref(30)
const calendarDays = ref<CalendarDay[]>([])

const summary = computed(() => {
  if (calendarDays.value.length === 0) return null
  const totalPages = calendarDays.value.reduce((s, d) => s + d.pages_read, 0)
  const totalTime = calendarDays.value.reduce((s, d) => s + d.time_seconds, 0)
  const activeDays = calendarDays.value.filter(d => d.pages_read > 0).length
  return { total_pages: totalPages, total_time: totalTime, active_days: activeDays }
})

const monthLabels = computed(() => {
  if (calendarDays.value.length === 0) return []
  const labels: { name: string; col: number; span: number }[] = []
  let currentMonth = ''
  let startCol = 1

  calendarDays.value.forEach((day, idx) => {
    const d = new Date(day.date)
    const monthName = `${d.getMonth() + 1}月`
    if (monthName !== currentMonth) {
      if (currentMonth) {
        labels.push({ name: currentMonth, col: startCol, span: idx - startCol + 1 })
      }
      currentMonth = monthName
      startCol = idx + 1
    }
  })
  if (currentMonth) {
    labels.push({ name: currentMonth, col: startCol, span: calendarDays.value.length - startCol + 1 })
  }
  return labels
})

function getHeatColor(pages: number): string {
  if (pages <= 0) return 'var(--bg-tertiary)'
  if (pages <= 5) return '#c6f6d5'
  if (pages <= 10) return '#9ae6b4'
  if (pages <= 20) return '#68d391'
  return '#38a169'
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

function formatMinutes(seconds: number): string {
  return Math.round(seconds / 60).toString()
}

onMounted(async () => {
  try {
    const resp = await getCalendar(days.value)
    calendarDays.value = resp.data.data.days
  } catch {
    calendarDays.value = []
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.reading-calendar {
  padding: 32px;
  max-width: 1000px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 28px;
}

.page-title {
  font-size: 26px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 4px 0;
  letter-spacing: -0.5px;
}

.page-subtitle {
  font-size: 14px;
  color: var(--text-tertiary);
  margin: 0;
}

.calendar-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 28px;
}

.summary-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-2xl);
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.summary-label {
  font-size: 13px;
  color: var(--text-tertiary);
}

.summary-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
}

.heatmap-container {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-2xl);
  padding: 24px;
}

.heatmap-legend {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
  margin-bottom: 16px;
}

.legend-label {
  font-size: 11px;
  color: var(--text-muted);
}

.legend-cell {
  width: 14px;
  height: 14px;
  border-radius: 3px;
}

.heatmap-grid {
  overflow-x: auto;
}

.heatmap-months {
  display: grid;
  grid-template-columns: repeat(v-bind('calendarDays.length'), 14px);
  gap: 3px;
  margin-bottom: 4px;
  padding-left: 32px;
}

.month-label {
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
}

.heatmap-body {
  display: flex;
  gap: 6px;
}

.heatmap-weekdays {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding-top: 2px;
  width: 26px;
  flex-shrink: 0;
}

.heatmap-weekdays span {
  font-size: 10px;
  color: var(--text-muted);
  height: 14px;
  line-height: 14px;
}

.heatmap-cells {
  display: grid;
  grid-template-columns: repeat(v-bind('calendarDays.length'), 14px);
  grid-template-rows: repeat(7, 14px);
  gap: 3px;
  grid-auto-flow: column;
}

.heatmap-cell {
  width: 14px;
  height: 14px;
  border-radius: 3px;
  cursor: pointer;
  transition: outline 0.1s;
}

.heatmap-cell:hover {
  outline: 2px solid var(--text-secondary);
  outline-offset: 1px;
}

.cell-inner {
  display: block;
  width: 100%;
  height: 100%;
}

.cell-tooltip {
  font-size: 12px;
  line-height: 1.6;
}
</style>