<template>
  <div class="dashboard mx-auto" style="max-width:1400px">

    <!-- ══════════════ Hero Zone — Welcome + Stats ══════════════ -->
    <section class="hero-zone">
      <!-- Decorative ink-wash watermark character -->
      <span class="hero-watermark">研</span>
      <div class="hero-bg"></div>
      <div class="hero-ink-top"></div>
      <div class="hero-ink-bottom"></div>

      <div class="hero-body">
        <div class="hero-text">
          <h1 class="hero-greeting">{{ greeting }}，<span class="hero-name">{{ displayName }}</span></h1>
          <p class="hero-date">{{ todayStr }} · 共阅读 {{ stats?.read_count || 0 }} 篇文献</p>
        </div>

        <div class="hero-stats" v-if="stats">
          <div class="hero-stat">
            <span class="hero-stat-value">{{ stats.total_literatures }}</span>
            <span class="hero-stat-label">
              <el-icon :size="12"><Collection /></el-icon>
              全部文献
            </span>
          </div>
          <div class="hero-stat-divider"></div>
          <div class="hero-stat">
            <span class="hero-stat-value">{{ stats.read_count }}</span>
            <span class="hero-stat-label">
              <el-icon :size="12"><Checked /></el-icon>
              已读
            </span>
          </div>
          <div class="hero-stat-divider"></div>
          <div class="hero-stat">
            <span class="hero-stat-value">{{ stats.unread_count }}</span>
            <span class="hero-stat-label">
              <el-icon :size="12"><Clock /></el-icon>
              未读
            </span>
          </div>
        </div>
      </div>
    </section>

    <!-- ══════════════ Reading Activity ══════════════ -->
    <section class="section section-activity">
      <div class="section-bar">
        <div class="section-bar-line"></div>
        <h2 class="section-title">阅读概览</h2>
        <span class="section-accent">WEEKLY</span>
      </div>

      <!-- Merged reading overview: calendar + stats side by side -->
      <div class="calendar-card" v-loading="calendarLoading">
        <div class="calendar-header">
          <div class="calendar-title-row">
            <el-icon :size="16"><Calendar /></el-icon>
            <span>阅读活动</span>
          </div>
          <span class="calendar-chip">近 30 天</span>
        </div>

        <div v-if="calendarDays.length > 0" class="cal-stacked">
          <!-- Full-width calendar area -->
          <div class="cal-months-area">
            <div v-for="(mb, mi) in monthBlocks" :key="mi" class="month-block" :style="{ '--delay': `${mi * 0.08}s` }">
              <div class="mb-title">{{ mb.monthName }}</div>
              <div class="mb-weekdays">
                <span v-for="wd in weekdays" :key="wd" class="mb-wd">{{ wd }}</span>
              </div>
              <div v-for="(week, wi) in mb.weeks" :key="wi" class="mb-week" :style="{ '--delay': `${(mi * 0.08) + wi * 0.03}s` }">
                <div v-for="(day, di) in week" :key="di" class="mb-cell"
                     :class="{
                       'mb-cell-active': day?.pages_read > 0,
                       'mb-cell-today': day && isToday(day.date)
                     }"
                     :style="{ background: day ? getHeatColor(day.pages_read) : 'transparent' }">
                  <el-tooltip v-if="day" placement="top" :show-after="300">
                    <template #content>
                      <div class="text-xs leading-relaxed">
                        <div>{{ formatDateOnly(day.date) }}</div>
                        <div>{{ day.pages_read }} 页 · {{ formatMinutes(day.time_seconds) }} 分钟</div>
                      </div>
                    </template>
                    <span class="mb-day">{{ getDayNumber(day.date) }}</span>
                  </el-tooltip>
                  <span v-if="day && isToday(day.date)" class="mb-today-dot"></span>
                </div>
              </div>
            </div>
            <div class="cal-legend">
              <span class="cal-legend-label">少</span>
              <div v-for="(level, idx) in heatColors" :key="idx" class="cal-legend-swatch" :style="{ background: level.color }" :title="level.label"></div>
              <span class="cal-legend-label">多</span>
              <span class="cal-legend-hint">· 颜色越深，当日阅读页数越多</span>
            </div>
          </div>

          <!-- Divider -->
          <div class="cal-divider"></div>

          <!-- Stats strip: 4 full-width stat cards -->
          <div class="cal-stats-strip" v-if="stats">
            <div class="cs-card">
              <div class="cs-icon" style="background:linear-gradient(135deg,rgba(2,132,199,0.12),rgba(2,132,199,0.03));color:var(--accent-primary)">
                <el-progress type="circle" :percentage="stats?.read_progress || 0" :width="40" :stroke-width="4" color="var(--accent-primary)" trail-color="rgba(2,132,199,0.06)" :stroke-linecap="'round'" class="progress-circle">
                  <span class="cs-pct">{{ stats?.read_progress || 0 }}%</span>
                </el-progress>
              </div>
              <span class="cs-value">{{ stats?.read_count || 0 }}/{{ stats?.total_literatures || 0 }}</span>
              <span class="cs-label">阅读进度</span>
              <span class="cs-desc">已读 {{ stats?.read_count || 0 }} / {{ stats?.total_literatures || 0 }} 篇</span>
            </div>
            <div class="cs-card">
              <div class="cs-icon" style="background:linear-gradient(135deg,rgba(16,185,129,0.12),rgba(16,185,129,0.03));color:var(--mint-600)">
                <el-icon :size="18"><Reading /></el-icon>
              </div>
              <span class="cs-value">{{ stats?.week_count || 0 }}</span>
              <span class="cs-label">本周阅读</span>
              <span class="cs-desc">{{ stats?.week_count || 0 }} 篇新增</span>
            </div>
            <div class="cs-card">
              <div class="cs-icon" style="background:linear-gradient(135deg,rgba(245,158,11,0.12),rgba(245,158,11,0.03));color:var(--amber-600)">
                <el-icon :size="18"><Collection /></el-icon>
              </div>
              <span class="cs-value">{{ stats?.month_count || 0 }}</span>
              <span class="cs-label">本月阅读</span>
              <span class="cs-desc">{{ stats?.month_count || 0 }} 篇累计</span>
            </div>
            <div class="cs-card">
              <div class="cs-icon" style="background:linear-gradient(135deg,rgba(56,189,248,0.12),rgba(56,189,248,0.03));color:var(--sky-600)">
                <el-icon :size="18"><Clock /></el-icon>
              </div>
              <span class="cs-value">{{ formatMinutes(stats?.avg_daily_time_seconds || 0) }}</span>
              <span class="cs-label">日均阅读</span>
              <span class="cs-desc">{{ formatMinutes(stats?.avg_daily_time_seconds || 0) }} 分钟/天</span>
            </div>
          </div>

          <!-- Activity bar: streak + yesterday + trend -->
          <div class="cal-activity-bar" v-if="calendarMeta">
            <div class="cab-group">
              <div class="cab-item cab-item-accent">
                <span class="cab-icon"><Reading /></span>
                <span>连续 <strong>{{ calendarMeta.streak }}</strong> 天</span>
              </div>
              <div class="cab-dot"></div>
              <div class="cab-item">
                <span class="cab-icon"><Collection /></span>
                <span>昨日 <strong>{{ calendarMeta.yesterday_pages }}</strong> 页</span>
              </div>
              <div class="cab-dot"></div>
              <div class="cab-item" :class="calendarMeta.week_trend >= 0 ? 'trend-up' : 'trend-down'">
                <span v-if="calendarMeta.week_trend >= 0">↑</span><span v-else>↓</span>
                <span>本周 {{ calendarMeta.week_trend >= 0 ? '+' : '' }}{{ calendarMeta.week_trend }}%</span>
              </div>
            </div>
          </div>
        </div>
        <el-empty v-else-if="!calendarLoading && rawCalendarDays.length === 0" description="暂无阅读记录，去阅读文献吧" :image-size="48" />
      </div>
    </section>

    <!-- ══════════════ Featured Papers ══════════════ -->
    <section class="section section-papers">
      <div class="section-bar">
        <div class="section-bar-line"></div>
        <h2 class="section-title">每日精选论文</h2>
        <span class="section-chip">数据来源：arXiv</span>
      </div>

      <el-skeleton v-if="featuredLoading" :rows="2" animated />

      <div v-else-if="featuredError" class="mb-3">
        <el-alert title="精选论文加载失败" type="info" :closable="false" show-icon />
      </div>

      <div v-else-if="featuredPapers.length === 0">
        <el-empty description="暂无精选论文" :image-size="60" />
      </div>

      <div v-else class="paper-grid">
        <div
          v-for="paper in featuredPapers"
          :key="paper.id"
          class="paper-card"
          @click="openArxivLink(paper.arxiv_url)"
        >
          <span class="paper-tag">{{ paper.category }}</span>
          <h4 class="paper-title">{{ paper.title }}</h4>
          <div class="paper-footer">
            <span class="paper-authors">{{ paper.authors }}</span>
            <span class="paper-date">{{ paper.published_date }}</span>
          </div>
        </div>
      </div>
    </section>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onActivated } from 'vue'
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
  { threshold: 1, color: '#e0f2fe', label: '1-5 页' },
  { threshold: 6, color: '#bae6fd', label: '6-10 页' },
  { threshold: 11, color: '#7dd3fc', label: '11-20 页' },
  { threshold: 21, color: '#38bdf8', label: '21+ 页' },
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

const calendarMeta = computed(() => {
  const days = rawCalendarDays.value
  if (days.length === 0) return null

  const totalPages = days.reduce((s, d) => s + d.pages_read, 0)
  const totalTime = Math.round(days.reduce((s, d) => s + d.time_seconds, 0) / 60)
  const activeDays = days.filter(d => d.pages_read > 0).length

  // Streak: consecutive days with pages_read > 0 from most recent backwards
  let streak = 0
  const sorted = [...days].sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
  for (const d of sorted) {
    if (d.pages_read > 0) streak++
    else break
  }

  // Yesterday pages
  const now = getBeijingNow()
  const yesterday = new Date(now)
  yesterday.setDate(yesterday.getDate() - 1)
  const yesterdayStr = yesterday.getFullYear() + '-' + String(yesterday.getMonth() + 1).padStart(2, '0') + '-' + String(yesterday.getDate()).padStart(2, '0')
  const yesterdayDay = days.find(d => d.date.startsWith(yesterdayStr))
  const yesterdayPages = yesterdayDay?.pages_read || 0

  // Week over week trend
  const nowMs = now.getTime()
  const weekMs = 7 * 24 * 60 * 60 * 1000
  const thisWeek = days.filter(d => {
    const t = new Date(d.date + 'T00:00:00').getTime()
    return t >= nowMs - weekMs && t <= nowMs
  })
  const lastWeek = days.filter(d => {
    const t = new Date(d.date + 'T00:00:00').getTime()
    return t >= nowMs - 2 * weekMs && t < nowMs - weekMs
  })
  const thisWeekPages = thisWeek.reduce((s, d) => s + d.pages_read, 0)
  const lastWeekPages = lastWeek.reduce((s, d) => s + d.pages_read, 0)
  const weekTrend = lastWeekPages > 0 ? ((thisWeekPages - lastWeekPages) / lastWeekPages * 100) : thisWeekPages > 0 ? 100 : 0

  return {
    total_pages: totalPages,
    total_time: totalTime,
    active_days: activeDays,
    streak,
    yesterday_pages: yesterdayPages,
    week_trend: Math.round(weekTrend * 10) / 10,
  }
})

const monthAccentColors = ['#0284c7', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899']

const monthBlocks = computed(() => {
  const days = calendarDays.value
  if (days.length === 0) return []
  // chunk into weeks of 7
  const weeks: (CalendarDay | null)[][] = []
  for (let i = 0; i < days.length; i += 7) {
    weeks.push(days.slice(i, i + 7))
  }
  // group weeks by month
  const blocks: { monthName: string; weeks: (CalendarDay | null)[][] }[] = []
  for (const week of weeks) {
    const first = week.find(d => d !== null)
    const month = first ? new Date(first.date).getMonth() + 1 + '月' : (blocks.length > 0 ? blocks[blocks.length - 1].monthName : '')
    if (blocks.length === 0 || blocks[blocks.length - 1].monthName !== month) {
      blocks.push({ monthName: month, weeks: [week] })
    } else {
      blocks[blocks.length - 1].weeks.push(week)
    }
  }
  return blocks
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

function isToday(dateStr: string): boolean {
  const normalized = dateStr.endsWith('Z') || dateStr.includes('+') ? dateStr : dateStr + 'Z'
  const d = new Date(normalized)
  const localOffset = -d.getTimezoneOffset()
  const bjDate = new Date(d.getTime() + (480 - localOffset) * 60000)
  const now = getBeijingNow()
  return bjDate.getFullYear() === now.getFullYear() &&
         bjDate.getMonth() === now.getMonth() &&
         bjDate.getDate() === now.getDate()
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

async function refreshFeatured() {
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
  refreshFeatured()
})

onActivated(() => {
  refreshFeatured()
})
</script>

<style scoped>
/* ═══════════════════════════════════════════════════════════════
   InkLight Dashboard — Vibrant Academic
   Warm, layered, energetic — built for young researchers
   ═══════════════════════════════════════════════════════════════ */

.dashboard {
  position: relative;
  padding: 28px 32px 56px;
  color: var(--text-primary);
  animation: fadeIn 0.5s ease both;
  min-height: 100%;
}

/* ── Paper grain noise overlay ── */
.dashboard::after {
  content: '';
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 9998;
  opacity: 0.025;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.75' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='300' height='300' filter='url(%23n)' opacity='0.5'/%3E%3C/svg%3E");
  background-repeat: repeat;
  background-size: 300px 300px;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* ══════════════════════════════════════════
   Section — shared component
   Now with colored background panels
   ══════════════════════════════════════════ */
.section {
  position: relative;
  margin-bottom: 32px;
  padding: 28px 24px 24px;
  border-radius: var(--radius-2xl);
  border: 1px solid var(--border-color);
}

/* Activity section — cool blue-tinted panel */
.section-activity {
  background:
    radial-gradient(ellipse at 90% 20%, rgba(2, 132, 199, 0.04) 0%, transparent 50%),
    var(--bg-overlay);
  backdrop-filter: blur(2px);
}

/* Papers section — warm mint-tinted panel */
.section-papers {
  background:
    radial-gradient(ellipse at 10% 30%, rgba(16, 185, 129, 0.04) 0%, transparent 50%),
    var(--bg-overlay);
  backdrop-filter: blur(2px);
}

/* Remove the gradient separator line since sections have visual borders now */
.section::after {
  display: none;
}

/* Subtle top accent line on section panels */
.section::before {
  content: '';
  position: absolute;
  top: 0;
  left: 24px;
  right: 24px;
  height: 2px;
  border-radius: 0 0 2px 2px;
  background: linear-gradient(90deg, transparent 0%, var(--sky-200) 30%, var(--sky-200) 70%, transparent 100%);
  opacity: 0.4;
}

.section-bar {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 22px;
}

.section-bar-line {
  width: 4px;
  height: 22px;
  border-radius: 3px;
  background: linear-gradient(180deg, var(--accent-primary) 0%, var(--sky-400) 100%);
  flex-shrink: 0;
}

.section-title {
  font-size: 18px;
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

.section-chip {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  padding: 3px 12px;
  border-radius: var(--radius-full);
  background: var(--slate-50);
  border: 1px solid var(--border-light);
  font-size: var(--text-xs);
  font-weight: 500;
  color: var(--text-tertiary);
  letter-spacing: 0.02em;
}

/* ══════════════════════════════════════════
   Hero Zone — ink-wash editorial
   ══════════════════════════════════════════ */
.hero-zone {
  position: relative;
  margin-bottom: 32px;
  padding: 0;
  overflow: hidden;
  border-radius: var(--radius-2xl);
}

/* Decorative "研" watermark character — larger, more presence */
.hero-watermark {
  position: absolute;
  top: -30px;
  right: 10px;
  font-family: 'Noto Serif SC', serif;
  font-size: 180px;
  font-weight: 900;
  color: transparent;
  line-height: 1;
  pointer-events: none;
  user-select: none;
  z-index: 0;
  background: linear-gradient(180deg, rgba(2, 132, 199, 0.05) 0%, rgba(16, 185, 129, 0.03) 60%, transparent 100%);
  -webkit-background-clip: text;
  background-clip: text;
  letter-spacing: -0.06em;
}

.hero-bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse at 80% 0%, rgba(2, 132, 199, 0.08) 0%, transparent 55%),
    radial-gradient(ellipse at 20% 100%, rgba(16, 185, 129, 0.06) 0%, transparent 45%),
    linear-gradient(165deg, #eef5ff 0%, #f8f5f0 35%, #f5efe8 60%, #edf7f0 100%);
  border-radius: var(--radius-2xl);
  pointer-events: none;
  z-index: 0;
}

/* Deep ink-wash accent at top right */
.hero-ink-top {
  position: absolute;
  top: -60px;
  right: -60px;
  width: 300px;
  height: 300px;
  border-radius: 50%;
  background: radial-gradient(circle at 40% 40%, rgba(2, 132, 199, 0.10) 0%, rgba(2, 132, 199, 0.03) 35%, transparent 65%);
  pointer-events: none;
  z-index: 0;
}

/* Soft glow at bottom left */
.hero-ink-bottom {
  position: absolute;
  bottom: -80px;
  left: 15%;
  width: 250px;
  height: 250px;
  border-radius: 50%;
  background: radial-gradient(circle at 50% 50%, rgba(16, 185, 129, 0.07) 0%, rgba(16, 185, 129, 0.02) 40%, transparent 65%);
  pointer-events: none;
  z-index: 0;
}

.hero-body {
  position: relative;
  z-index: 1;
  padding: 40px 44px;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 32px;
}

.hero-text {
  flex: 1;
  min-width: 0;
}

.hero-greeting {
  font-family: 'Noto Serif SC', serif;
  font-size: 38px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px 0;
  line-height: 1.2;
  letter-spacing: -0.025em;
  text-wrap: balance;
}

.hero-name {
  color: var(--accent-primary);
}

.hero-date {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
  margin: 0;
  letter-spacing: 0.01em;
}

.hero-stats {
  display: flex;
  align-items: center;
  gap: 0;
  flex-shrink: 0;
  background: var(--bg-overlay);
  backdrop-filter: blur(6px);
  border-radius: var(--radius-xl);
  padding: 12px 8px;
  border: 1px solid var(--border-color);
}

.hero-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 0 20px;
}

.hero-stat:first-child { padding-left: 4px; }
.hero-stat:last-child { padding-right: 4px; }

.hero-stat-value {
  font-size: 28px;
  font-weight: 800;
  color: var(--text-primary);
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.hero-stat-label {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: var(--text-xs);
  font-weight: 500;
  color: var(--text-tertiary);
  white-space: nowrap;
}

.hero-stat-divider {
  width: 1px;
  height: 36px;
  background: linear-gradient(180deg, transparent 0%, var(--border-color) 30%, var(--border-color) 70%, transparent 100%);
  flex-shrink: 0;
}

/* ══════════════════════════════════════════
   Stacked layout — calendar, stats, activity
   ══════════════════════════════════════════ */
.cal-stacked {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.cal-divider {
  height: 1px;
  background: linear-gradient(90deg, transparent 0%, var(--border-color) 15%, var(--border-color) 85%, transparent 100%);
  margin: 20px 0 18px;
  flex-shrink: 0;
}

/* Stats strip: 4 rich cards in a single row */
.cal-stats-strip {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-bottom: 16px;
}

.cs-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  padding: 14px 8px 12px;
  border-radius: var(--radius-lg);
  background: var(--bg-overlay);
  border: 1px solid var(--border-color);
  text-align: center;
  transition: all 0.25s cubic-bezier(0.22, 1, 0.36, 1);
}

.cs-card:hover {
  background: var(--bg-overlay-hover);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px -6px rgba(2, 132, 199, 0.08);
}

.cs-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 12px;
  margin-bottom: 2px;
  flex-shrink: 0;
}

.cs-pct {
  font-size: 12px;
  font-weight: 700;
  color: var(--accent-primary);
  line-height: 1;
}

/* ── Force progress circle text to truly center ── */
.cs-card :deep(.el-progress--circle .el-progress__text) {
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  inset: 0 !important;
  transform: none !important;
}

.cs-value {
  font-size: 18px;
  font-weight: 800;
  color: var(--text-primary);
  line-height: 1.3;
  font-variant-numeric: tabular-nums;
}

.cs-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  letter-spacing: 0.02em;
}

.cs-desc {
  font-size: 10px;
  font-weight: 400;
  color: var(--text-muted);
  margin-top: 0;
}

/* Activity bar — streak, yesterday, trend */
.cal-activity-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px 16px;
  border-radius: var(--radius-lg);
  background: var(--bg-overlay);
  border: 1px solid var(--border-color);
}

.cab-group {
  display: flex;
  align-items: center;
  gap: 14px;
}

.cab-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-tertiary);
  white-space: nowrap;
}

.cab-item strong {
  font-weight: 700;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

.cab-item-accent {
  color: var(--accent-primary);
}

.cab-item-accent strong {
  color: var(--accent-primary);
}

.cab-dot {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: var(--border-color);
  flex-shrink: 0;
}

.cab-icon {
  display: inline-flex;
  align-items: center;
  color: inherit;
  font-size: 14px;
  line-height: 1;
}

.cal-legend-hint {
  font-size: 10px;
  font-weight: 400;
  color: var(--text-muted);
  margin-left: 2px;
}

/* ══════════════════════════════════════════
   Calendar card
   ══════════════════════════════════════════ */
.calendar-card {
  background: var(--bg-overlay-heavy);
  backdrop-filter: blur(4px);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  padding: var(--space-6);
  box-shadow: 0 1px 3px rgba(0,0,0,0.02);
  transition: all 0.25s cubic-bezier(0.22, 1, 0.36, 1);
}

.calendar-card:hover {
  box-shadow: 0 8px 28px -8px rgba(2, 132, 199, 0.08), 0 2px 6px -2px rgba(0,0,0,0.02);
  border-color: var(--accent-light);
}

.calendar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
}

.calendar-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
}

.calendar-chip {
  display: inline-flex;
  align-items: center;
  padding: 3px 12px;
  border-radius: var(--radius-full);
  background: var(--slate-50);
  border: 1px solid var(--border-light);
  font-size: var(--text-xs);
  font-weight: 500;
  color: var(--text-tertiary);
}

.trend-up {
  color: var(--mint-600);
  font-weight: 600;
}

.trend-down {
  color: var(--rose-500);
  font-weight: 600;
}

.cal-months-area {
  flex: 1;
  min-width: 0;
  display: flex;
  gap: var(--space-5);
  align-items: flex-start;
}

.month-block {
  flex: 1;
  min-width: 0;
}

.mb-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 4px;
  letter-spacing: 0.02em;
}

.mb-weekdays {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 1px;
  margin-bottom: 3px;
  padding: 0 1px;
}

.mb-wd {
  text-align: center;
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted);
  height: 18px;
  line-height: 18px;
}

.mb-week {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 1px;
  padding: 0 1px;
  margin-bottom: 1px;
}

.mb-cell {
  height: 28px;
  width: 100%;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: outline var(--transition-fast), transform var(--transition-fast);
  position: relative;
}

.mb-cell:hover {
  outline: 2px solid var(--slate-400);
  outline-offset: 1px;
  transform: scale(1.15);
  z-index: 1;
}

.mb-cell-active {
  outline: 1px solid rgba(255,255,255,0.3);
  outline-offset: -1px;
}

.mb-day {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  line-height: 1;
}

.mb-cell-active .mb-day {
  color: #fff;
  font-weight: 700;
  text-shadow: 0 1px 3px rgba(0,0,0,0.2);
}

.mb-cell-today {
  outline: 2px solid var(--accent-primary) !important;
  outline-offset: 1px;
  position: relative;
}

.mb-today-dot {
  position: absolute;
  bottom: 1px;
  left: 50%;
  transform: translateX(-50%);
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: var(--accent-primary);
  animation: todayPulse 2s ease-in-out infinite;
}

@keyframes todayPulse {
  0%, 100% { opacity: 1; transform: translateX(-50%) scale(1); }
  50% { opacity: 0.3; transform: translateX(-50%) scale(1.6); }
}

/* Legend */
.cal-legend {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-color);
  justify-content: flex-end;
}

.cal-legend-label {
  font-size: 10px;
  font-weight: 500;
  color: var(--text-muted);
}

.cal-legend-swatch {
  width: 12px;
  height: 12px;
  border-radius: 3px;
}

.cal-legend-divider {
  width: 1px;
  height: 12px;
  background: var(--border-color);
  margin: 0 4px;
}

.cal-legend-text {
  font-size: 10px;
  font-weight: 400;
  color: var(--text-muted);
}

/* ══════════════════════════════════════════
   Featured paper cards — with colored accents
   ══════════════════════════════════════════ */
.paper-grid {
  display: grid;
  gap: var(--space-3);
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
}

.paper-card {
  --card-accent: rgba(2, 132, 199, 0.35);
  background:
    linear-gradient(to bottom,
      var(--card-accent) 0px,
      var(--card-accent) 3px,
      rgba(255, 255, 255, 0.85) 3px,
      rgba(255, 255, 255, 0.85) 100%);
  backdrop-filter: blur(6px);
  border: 1px solid rgba(148, 163, 184, 0.3);
  border-radius: var(--radius-lg);
  padding: 20px 22px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.22, 1, 0.36, 1);
  display: flex;
  flex-direction: column;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06), 0 0 0 1px rgba(0, 0, 0, 0.02);
  position: relative;
}

/* Alternate accent colors across cards */
.paper-card:nth-child(3n-1) { --card-accent: rgba(16, 185, 129, 0.35); }
.paper-card:nth-child(3n) { --card-accent: rgba(245, 158, 11, 0.3); }

.paper-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 28px -6px rgba(2, 132, 199, 0.15), 0 2px 6px rgba(0, 0, 0, 0.08);
  border-color: rgba(2, 132, 199, 0.45);
  background:
    linear-gradient(to bottom,
      var(--card-accent) 0px,
      var(--card-accent) 3px,
      rgba(255, 255, 255, 0.95) 3px,
      rgba(255, 255, 255, 0.95) 100%);
}

.paper-tag {
  display: inline-flex;
  align-self: flex-start;
  padding: 2px 10px;
  border-radius: var(--radius-sm);
  background: var(--sky-50);
  color: var(--accent-primary);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.02em;
  margin-bottom: 10px;
}

.paper-title {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 auto 0;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  flex: 1;
}

.paper-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid rgba(226, 232, 240, 0.5);
}

.paper-authors {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  flex: 1 1 auto;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.paper-date {
  font-size: var(--text-xs);
  color: var(--text-muted);
  flex-shrink: 0;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}
</style>
