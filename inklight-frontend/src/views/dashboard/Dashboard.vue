<template>
  <div class="dashboard px-8 py-6 mx-auto" style="max-width:1400px">
    <!-- Welcome -->
    <div class="welcome-section mb-6 relative">
      <h1 class="text-3xl font-extrabold m-0 mb-1" :style="{ letterSpacing: '-0.02em', lineHeight: '1.25' }">{{ greeting }}，{{ displayName }}</h1>
      <p class="text-sm m-0">今天是 {{ todayStr }}，共阅读 {{ stats?.read_count || 0 }} 篇文献</p>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid mb-4">
      <div class="stat-card stat-card-total">
        <div class="stat-icon" :style="{ background: 'var(--gradient-primary-subtle)', color: 'var(--accent-primary)' }">
          <el-icon :size="20"><Collection /></el-icon>
        </div>
        <div class="stat-info">
          <p class="stat-value">{{ stats?.total_literatures || 0 }}</p>
          <p class="stat-label">全部文献</p>
        </div>
      </div>
      <div class="stat-card stat-card-read">
        <div class="stat-icon" :style="{ background: 'linear-gradient(135deg, var(--mint-50), var(--mint-100))', color: 'var(--mint-600)' }">
          <el-icon :size="20"><Checked /></el-icon>
        </div>
        <div class="stat-info">
          <p class="stat-value">{{ stats?.read_count || 0 }}</p>
          <p class="stat-label">已读</p>
        </div>
      </div>
      <div class="stat-card stat-card-unread">
        <div class="stat-icon" :style="{ background: 'var(--gradient-warm)', color: 'var(--amber-600)' }">
          <el-icon :size="20"><Clock /></el-icon>
        </div>
        <div class="stat-info">
          <p class="stat-value">{{ stats?.unread_count || 0 }}</p>
          <p class="stat-label">未读</p>
        </div>
      </div>
    </div>

    <!-- 阅读进度 -->
    <div class="reading-stats-grid mb-4">
      <div class="reading-stat-card" :style="{ borderTop: '3px solid #0284c7' }">
        <div class="flex flex-col items-center gap-1_5 px-5 py-4">
          <div class="w-full text-center">
            <span class="stat-label" :style="{ color: 'var(--accent-primary)' }">阅读进度</span>
          </div>
          <el-progress type="circle" :percentage="stats?.read_progress || 0" :width="80" :stroke-width="8" color="var(--accent-primary)" />
          <div class="text-xs">已读 {{ stats?.read_count || 0 }} / {{ stats?.total_literatures || 0 }} 篇</div>
        </div>
      </div>
      <div class="reading-stat-card" :style="{ borderTop: '3px solid #0ea5e9' }">
        <div class="flex flex-col items-center gap-1_5 px-5 py-4">
          <div class="w-full text-center">
            <span class="stat-label" :style="{ color: '#0ea5e9' }">本周阅读</span>
          </div>
          <div class="text-3xl font-extrabold leading-none mt-1 tracking-tight">{{ stats?.week_count || 0 }}</div>
          <div class="text-xs">篇</div>
        </div>
      </div>
      <div class="reading-stat-card" :style="{ borderTop: '3px solid #8b5cf6' }">
        <div class="flex flex-col items-center gap-1_5 px-5 py-4">
          <div class="w-full text-center">
            <span class="stat-label" :style="{ color: '#7c3aed' }">本月阅读</span>
          </div>
          <div class="text-3xl font-extrabold leading-none mt-1 tracking-tight">{{ stats?.month_count || 0 }}</div>
          <div class="text-xs">篇</div>
        </div>
      </div>
      <div class="reading-stat-card" :style="{ borderTop: '3px solid var(--amber-500)' }">
        <div class="flex flex-col items-center gap-1_5 px-5 py-4">
          <div class="w-full text-center">
            <span class="stat-label" :style="{ color: 'var(--amber-600)' }">日均阅读</span>
          </div>
          <div class="text-3xl font-extrabold leading-none mt-1 tracking-tight">{{ formatMinutes(stats?.avg_daily_time_seconds || 0) }}</div>
          <div class="text-xs">分钟</div>
        </div>
      </div>
    </div>

    <!-- 阅读日历热力图 -->
    <div class="content-card mb-6" v-loading="calendarLoading">
      <div class="section-header">
        <h3 class="section-title">
          <el-icon :size="18"><Calendar /></el-icon>
          阅读日历
        </h3>
        <span class="px-2 py-0_5 text-xs rounded-full bg-slate-50">近 30 天</span>
      </div>

      <div class="calendar-summary" v-if="calendarSummary">
        <div class="cal-stat-item">
          <span class="text-xl font-extrabold leading-none tracking-tight">{{ calendarSummary.total_pages }}</span>
          <span class="text-xs font-medium">总阅读页数</span>
        </div>
        <div class="cal-stat-divider"></div>
        <div class="cal-stat-item">
          <span class="text-xl font-extrabold leading-none tracking-tight">{{ calendarSummary.active_days }}</span>
          <span class="text-xs font-medium">活跃天数</span>
        </div>
        <div class="cal-stat-divider"></div>
        <div class="cal-stat-item">
          <span class="text-xl font-extrabold leading-none tracking-tight">{{ calendarSummary.total_time }}</span>
          <span class="text-xs font-medium">总阅读分钟</span>
        </div>
      </div>

      <div class="overflow-x-auto pb-2" v-if="calendarDays.length > 0">
        <div class="flex items-center justify-end gap-1 mb-3">
          <span class="text-xs">少</span>
          <div v-for="(level, idx) in heatColors" :key="idx" class="rounded-xs" style="width:14px;height:14px" :style="{ background: level.color }" :title="level.label"></div>
          <span class="text-xs">多</span>
        </div>
        <div class="min-w-[200px]" v-if="weekCount > 0">
          <div class="heatmap-months" :style="{ gridTemplateColumns: `repeat(${weekCount}, 32px)` }">
            <span v-for="(label, idx) in monthLabels" :key="idx" class="month-label"
              :style="{ gridColumn: label.col + ' / span ' + label.span }">{{ label.name }}</span>
          </div>
          <div class="flex gap-1_5">
            <div class="flex flex-col gap-1 w-[26px] flex-shrink-0">
              <span v-for="wd in weekdays" :key="wd" class="text-xs h-8 leading-8 text-center">{{ wd }}</span>
            </div>
            <div class="grid gap-1" :style="{ gridTemplateColumns: `repeat(${weekCount}, 32px)`, gridTemplateRows: `repeat(7, 32px)`, gridAutoFlow: 'column' }">
              <template v-for="(day, idx) in calendarDays" :key="idx">
                <div v-if="day" class="heatmap-cell w-8 h-8 rounded-xs cursor-pointer flex items-center justify-center transition-all duration-150"
                     :class="{ 'has-activity': day.pages_read > 0 }" :style="{ background: getHeatColor(day.pages_read) }">
                  <el-tooltip placement="top" :show-after="200">
                    <template #content>
                      <div class="text-xs leading-relaxed">
                        <div>{{ formatDateOnly(day.date) }}</div>
                        <div>{{ day.pages_read }} 页 · {{ formatMinutes(day.time_seconds) }} 分钟</div>
                      </div>
                    </template>
                    <span class="cell-date text-xs font-medium leading-none">{{ getDayNumber(day.date) }}</span>
                  </el-tooltip>
                </div>
                <div v-else class="w-8 h-8 rounded-xs pointer-events-none"></div>
              </template>
            </div>
          </div>
        </div>
        <el-empty v-else-if="!calendarLoading && rawCalendarDays.length === 0" description="暂无阅读记录，去阅读文献吧" :image-size="48" />
      </div>
    </div>

    <!-- 每日精选论文 -->
    <div class="content-card mb-6">
      <div class="section-header">
        <h3 class="section-title">
          <el-icon :size="18"><Reading /></el-icon>
          每日精选论文
        </h3>
        <span class="px-2 py-0_5 text-xs rounded-full bg-slate-50">数据来源：arXiv</span>
      </div>

      <el-skeleton v-if="featuredLoading" :rows="2" animated />

      <div v-else-if="featuredError" class="mb-3">
        <el-alert title="精选论文加载失败" type="info" :closable="false" show-icon />
      </div>

      <div v-else-if="featuredPapers.length === 0">
        <el-empty description="暂无精选论文" :image-size="60" />
      </div>

      <div v-else class="grid gap-3" style="grid-template-columns:repeat(auto-fill,minmax(300px,1fr))">
        <el-card
          v-for="paper in featuredPapers"
          :key="paper.id"
          class="featured-card cursor-pointer rounded-lg border transition-all duration-200"
          shadow="hover"
          @click="openArxivLink(paper.arxiv_url)"
        >
          <div class="flex items-center justify-between mb-2">
            <el-tag size="small" effect="plain" class="text-[11px]">{{ paper.category }}</el-tag>
            <span class="text-[11px]">{{ paper.published_date }}</span>
          </div>
          <h4 class="text-base font-semibold m-0 mb-1 leading-normal line-clamp-2">{{ paper.title }}</h4>
          <p class="text-xs m-0 truncate">{{ paper.authors }}</p>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { getReadingStats, getCalendar, type ReadingStats, type CalendarDay } from '@/api/stats'
import { fetchFeaturedPapers } from '@/api/featured'
import type { FeaturedPaper } from '@/api/featured'
import { Collection, Checked, Clock, Calendar, Reading } from '@element-plus/icons-vue'
import { formatDateOnly, getBeijingNow } from '@/utils/time'

const authStore = useAuthStore()

const stats = ref<ReadingStats | null>(null)

// ── Calendar ──
const calendarLoading = ref(true)
const rawCalendarDays = ref<CalendarDay[]>([])

const heatColors = [
  { threshold: 0, color: 'var(--bg-tertiary)', label: '0 页' },
  { threshold: 1, color: '#c6f6d5', label: '1-5 页' },
  { threshold: 6, color: '#9ae6b4', label: '6-10 页' },
  { threshold: 11, color: '#68d391', label: '11-20 页' },
  { threshold: 21, color: '#38a169', label: '21+ 页' },
]

const weekdays = ['一', '二', '三', '四', '五', '六', '日']

const calendarDays = computed(() => {
  const data = rawCalendarDays.value
  if (data.length === 0) return []
  const firstDate = new Date(data[0].date)
  const jsDay = firstDate.getDay()
  const offset = (jsDay + 6) % 7
  const padded: (CalendarDay | null)[] = []
  for (let i = 0; i < offset; i++) padded.push(null)
  for (const d of data) padded.push(d)
  return padded
})

const weekCount = computed(() => Math.ceil(calendarDays.value.length / 7))

const calendarSummary = computed(() => {
  if (rawCalendarDays.value.length === 0) return null
  const totalPages = rawCalendarDays.value.reduce((s, d) => s + d.pages_read, 0)
  const totalTime = rawCalendarDays.value.reduce((s, d) => s + d.time_seconds, 0)
  const activeDays = rawCalendarDays.value.filter(d => d.pages_read > 0).length
  return { total_pages: totalPages, total_time: Math.round(totalTime / 60), active_days: activeDays }
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
  if (pages <= 0) return heatColors[0].color
  if (pages <= 5) return heatColors[1].color
  if (pages <= 10) return heatColors[2].color
  if (pages <= 20) return heatColors[3].color
  return heatColors[4].color
}

function getDayNumber(dateStr: string): string {
  const normalized = dateStr.endsWith('Z') || dateStr.includes('+') ? dateStr : dateStr + 'Z'
  const d = new Date(normalized)
  const localOffset = -d.getTimezoneOffset()
  const bjDate = new Date(d.getTime() + (480 - localOffset) * 60000)
  return String(bjDate.getDate())
}

function formatMinutes(seconds: number): string {
  if (!seconds || seconds <= 0) return '0'
  return Math.round(seconds / 60).toString()
}

/* ── Featured Papers ── */
const featuredPapers = ref<FeaturedPaper[]>([])
const featuredLoading = ref(false)
const featuredError = ref(false)

const weekDays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']
const todayBJ = getBeijingNow()
const todayStr = computed(() => {
  return `${todayBJ.getFullYear()}年${todayBJ.getMonth() + 1}月${todayBJ.getDate()}日 ${weekDays[todayBJ.getDay()]}`
})

const hours = todayBJ.getHours()
const greeting = computed(() => {
  if (hours < 6) return '夜深了'
  if (hours < 9) return '早上好'
  if (hours < 12) return '上午好'
  if (hours < 14) return '中午好'
  if (hours < 18) return '下午好'
  return '晚上好'
})

const displayName = computed(() => {
  return authStore.user?.username || authStore.user?.email?.split('@')[0] || '用户'
})

function openArxivLink(url: string) {
  window.open(url, '_blank')
}

async function loadCalendar() {
  calendarLoading.value = true
  try {
    const resp = await getCalendar(30)
    rawCalendarDays.value = resp.data.data.days
  } catch {
    rawCalendarDays.value = []
  } finally {
    calendarLoading.value = false
  }
}

async function loadStats() {
  try {
    const resp = await getReadingStats()
    stats.value = resp.data.data
  } catch { /* ignore */ }
}

async function loadFeaturedPapers() {
  featuredLoading.value = true
  featuredError.value = false
  try {
    const data = await fetchFeaturedPapers(15)
    featuredPapers.value = data.items
  } catch {
    featuredError.value = true
  } finally {
    featuredLoading.value = false
  }
}

onMounted(() => {
  loadStats()
  loadCalendar()
  loadFeaturedPapers()
})
</script>

<style scoped>
.dashboard { color: var(--text-primary); }

/* Welcome */
.welcome-section::after {
  content: '';
  position: absolute;
  bottom: -12px;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, var(--accent-primary), transparent 80%);
  opacity: 0.15;
}

.welcome-section h1 { color: var(--text-primary); }
.welcome-section p { color: var(--text-tertiary); }

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-4);
}

.stat-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  padding: 18px 20px;
  display: flex;
  align-items: center;
  gap: 14px;
  box-shadow: var(--shadow-xs);
  position: relative;
  overflow: hidden;
  transition: all var(--transition-base);
}

.stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 3px;
  height: 100%;
  opacity: 0;
  transition: opacity var(--transition-base);
}

.stat-card-total::before { background: var(--gradient-primary); }
.stat-card-read::before { background: linear-gradient(180deg, var(--mint-500), var(--mint-400)); }
.stat-card-unread::before { background: linear-gradient(180deg, var(--amber-500), var(--amber-600)); }

.stat-card:hover { box-shadow: var(--shadow-card-hover); transform: translateY(-2px); }
.stat-card:hover::before { opacity: 1; }

.stat-icon {
  width: 42px;
  height: 42px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-info { flex: 1; }
.stat-value { font-size: var(--text-2xl); font-weight: 800; color: var(--text-primary); margin: 0 0 var(--space-1) 0; line-height: 1; letter-spacing: var(--tracking-tight); }
.stat-label { font-size: var(--text-xs); color: var(--text-tertiary); margin: 0; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; }

/* Reading Stats */
.reading-stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-3);
}

.reading-stat-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xs);
  transition: all var(--transition-base);
  overflow: hidden;
  position: relative;
}

.reading-stat-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-card-hover); }
.reading-stat-card:first-child:hover { border-color: var(--accent-primary); }
.reading-stat-card:nth-child(2):hover { border-color: #0ea5e9; }
.reading-stat-card:nth-child(3):hover { border-color: #8b5cf6; }
.reading-stat-card:nth-child(4):hover { border-color: var(--amber-500); }

/* Calendar Section */
.calendar-summary {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-8);
  margin-bottom: var(--space-5);
  padding: var(--space-3) var(--space-4);
  background: var(--gradient-primary-subtle);
  border-radius: var(--radius-lg);
}

.cal-stat-item { display: flex; flex-direction: column; align-items: center; gap: 2px; }

.cal-stat-divider { width: 1px; height: 36px; background: var(--border-color); }

.heatmap-months {
  display: grid;
  gap: 4px;
  margin-bottom: 4px;
  padding-left: 32px;
}

.month-label {
  font-size: var(--text-xs);
  color: var(--text-muted);
  white-space: nowrap;
  font-weight: 500;
}

.heatmap-cell { transition: outline var(--transition-fast), transform var(--transition-fast); }
.heatmap-cell:hover { outline: 2px solid var(--text-secondary); outline-offset: 1px; transform: scale(1.1); z-index: 1; }
.cell-date { color: var(--text-secondary); }
.heatmap-cell.has-activity .cell-date { color: #fff; font-weight: 600; text-shadow: 0 1px 2px rgba(0,0,0,0.2); }

/* Featured */
.featured-card {
  border: 1px solid var(--border-color);
  background: var(--bg-primary);
}

.featured-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-card-hover);
  border-color: var(--accent-primary);
}
</style>
