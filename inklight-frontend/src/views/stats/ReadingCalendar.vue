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
          v-for="(level, idx) in legendLevels"
          :key="idx"
          class="legend-cell"
          :style="{ background: level.color }"
          :title="level.label"
        ></div>
        <span class="legend-label">多</span>
      </div>

      <div class="heatmap-grid" v-if="weekCount > 0">
        <div
          class="heatmap-months"
          :style="{ gridTemplateColumns: `repeat(${weekCount}, 32px)` }"
        >
          <span
            v-for="(label, idx) in monthLabels"
            :key="idx"
            class="month-label"
            :style="{ gridColumn: label.col + ' / span ' + label.span }"
          >{{ label.name }}</span>
        </div>
        <div class="heatmap-body">
          <div class="heatmap-weekdays">
            <span v-for="wd in weekdays" :key="wd">{{ wd }}</span>
          </div>
          <div
            class="heatmap-cells"
            :style="{
              gridTemplateColumns: `repeat(${weekCount}, 32px)`,
              gridTemplateRows: `repeat(7, 32px)`,
            }"
          >
            <template v-for="(day, idx) in calendarDays" :key="idx">
              <div
                v-if="day"
                class="heatmap-cell"
                :class="{ 'has-activity': day.pages_read > 0 }"
                :style="{ background: getHeatColor(day.pages_read) }"
              >
                <el-tooltip placement="top" :show-after="200">
                  <template #content>
                    <div class="cell-tooltip">
                      <div>{{ formatDate(day.date) }}</div>
                      <div>{{ day.pages_read }} 页 · {{ formatMinutes(day.time_seconds) }} 分钟</div>
                    </div>
                  </template>
                  <span class="cell-date">{{ getDayNumber(day.date) }}</span>
                </el-tooltip>
              </div>
              <div v-else class="heatmap-cell heatmap-cell-empty"></div>
            </template>
          </div>
        </div>
      </div>
    </div>

    <el-empty v-if="!loading && rawDays.length === 0" description="暂无阅读记录，去阅读文献吧" />
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
const rawDays = ref<CalendarDay[]>([])

const weekdays = ['一', '二', '三', '四', '五', '六', '日']

const HEAT_COLORS = [
  { threshold: 0, color: 'var(--bg-tertiary)', label: '0 页' },
  { threshold: 1, color: '#c6f6d5', label: '1-5 页' },
  { threshold: 6, color: '#9ae6b4', label: '6-10 页' },
  { threshold: 11, color: '#68d391', label: '11-20 页' },
  { threshold: 21, color: '#38a169', label: '21+ 页' },
]

const legendLevels = computed(() => HEAT_COLORS)

const calendarDays = computed(() => {
  const data = rawDays.value
  if (data.length === 0) return []

  const firstDate = new Date(data[0].date)
  const jsDay = firstDate.getDay()
  const offset = (jsDay + 6) % 7

  const padded: (CalendarDay | null)[] = []
  for (let i = 0; i < offset; i++) {
    padded.push(null)
  }
  for (const d of data) {
    padded.push(d)
  }

  return padded
})

const weekCount = computed(() => Math.ceil(calendarDays.value.length / 7))

const summary = computed(() => {
  if (rawDays.value.length === 0) return null
  const totalPages = rawDays.value.reduce((s, d) => s + d.pages_read, 0)
  const totalTime = rawDays.value.reduce((s, d) => s + d.time_seconds, 0)
  const activeDays = rawDays.value.filter(d => d.pages_read > 0).length
  return { total_pages: totalPages, total_time: totalTime, active_days: activeDays }
})

const monthLabels = computed(() => {
  const data = calendarDays.value
  if (data.length === 0) return []
  const labels: { name: string; col: number; span: number }[] = []
  let currentMonth = ''
  let startWeek = 1
  let spanWeeks = 0

  data.forEach((day, idx) => {
    const weekCol = Math.floor(idx / 7) + 1
    if (!day) {
      if (currentMonth) spanWeeks = weekCol - startWeek + 1
      return
    }
    const d = new Date(day.date)
    const monthName = `${d.getMonth() + 1}月`
    if (monthName !== currentMonth) {
      if (currentMonth && spanWeeks > 0) {
        labels.push({ name: currentMonth, col: startWeek, span: spanWeeks })
      }
      currentMonth = monthName
      startWeek = weekCol
      spanWeeks = 1
    } else {
      spanWeeks = weekCol - startWeek + 1
    }
  })
  if (currentMonth && spanWeeks > 0) {
    labels.push({ name: currentMonth, col: startWeek, span: spanWeeks })
  }
  return labels
})

function getHeatColor(pages: number): string {
  if (pages <= 0) return HEAT_COLORS[0].color
  if (pages <= 5) return HEAT_COLORS[1].color
  if (pages <= 10) return HEAT_COLORS[2].color
  if (pages <= 20) return HEAT_COLORS[3].color
  return HEAT_COLORS[4].color
}

function getDayNumber(dateStr: string): string {
  const d = new Date(dateStr)
  return String(d.getDate())
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
    rawDays.value = resp.data.data.days
  } catch {
    rawDays.value = []
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
  gap: 4px;
  margin-bottom: 4px;
  padding-left: 32px;
}

.month-label {
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
  font-weight: 500;
}

.heatmap-body {
  display: flex;
  gap: 6px;
}

.heatmap-weekdays {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 26px;
  flex-shrink: 0;
}

.heatmap-weekdays span {
  font-size: 11px;
  color: var(--text-muted);
  height: 32px;
  line-height: 32px;
  text-align: center;
}

.heatmap-cells {
  display: grid;
  gap: 4px;
  grid-auto-flow: column;
}

.heatmap-cell {
  width: 32px;
  height: 32px;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: outline 0.1s, transform 0.1s;
}

.heatmap-cell:hover {
  outline: 2px solid var(--text-secondary);
  outline-offset: 1px;
  transform: scale(1.1);
  z-index: 1;
}

.heatmap-cell-empty {
  background: transparent;
  cursor: default;
  pointer-events: none;
}

.cell-date {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  line-height: 1;
}

.heatmap-cell.has-activity .cell-date {
  color: #fff;
  font-weight: 600;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.cell-tooltip {
  font-size: 12px;
  line-height: 1.6;
}
</style>