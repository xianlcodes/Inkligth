<template>
  <div class="dashboard">
    <div class="welcome-section">
      <h1 class="welcome-title">{{ greeting }}，{{ displayName }}</h1>
      <p class="welcome-subtitle">今天是 {{ todayStr }}，共阅读 {{ stats?.read_count || 0 }} 篇文献</p>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-icon stat-icon--total">
          <el-icon :size="20"><Collection /></el-icon>
        </div>
        <div class="stat-info">
          <p class="stat-value">{{ stats?.total_literatures || 0 }}</p>
          <p class="stat-label">全部文献</p>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-icon--read">
          <el-icon :size="20"><Checked /></el-icon>
        </div>
        <div class="stat-info">
          <p class="stat-value">{{ stats?.read_count || 0 }}</p>
          <p class="stat-label">已读</p>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-icon--unread">
          <el-icon :size="20"><Clock /></el-icon>
        </div>
        <div class="stat-info">
          <p class="stat-value">{{ stats?.unread_count || 0 }}</p>
          <p class="stat-label">未读</p>
        </div>
      </div>
    </div>

    <!-- 阅读进度 -->
    <div class="reading-stats-row">
      <div class="reading-stat-card reading-stat-card--progress">
        <div class="reading-stat-accent-bar"></div>
        <div class="reading-stat-body">
          <div class="reading-stat-header">
            <span class="reading-stat-label">阅读进度</span>
          </div>
          <div class="progress-ring-wrapper">
            <el-progress
              type="circle"
              :percentage="stats?.read_progress || 0"
              :width="80"
              :stroke-width="8"
              color="var(--accent-primary)"
            />
          </div>
          <div class="reading-stat-detail">
            <span>已读 {{ stats?.read_count || 0 }} / {{ stats?.total_literatures || 0 }} 篇</span>
          </div>
        </div>
      </div>
      <div class="reading-stat-card reading-stat-card--week">
        <div class="reading-stat-accent-bar"></div>
        <div class="reading-stat-body">
          <div class="reading-stat-header">
            <span class="reading-stat-label">本周阅读</span>
          </div>
          <div class="reading-stat-big-number">{{ stats?.week_count || 0 }}</div>
          <div class="reading-stat-detail">篇</div>
        </div>
      </div>
      <div class="reading-stat-card reading-stat-card--month">
        <div class="reading-stat-accent-bar"></div>
        <div class="reading-stat-body">
          <div class="reading-stat-header">
            <span class="reading-stat-label">本月阅读</span>
          </div>
          <div class="reading-stat-big-number">{{ stats?.month_count || 0 }}</div>
          <div class="reading-stat-detail">篇</div>
        </div>
      </div>
      <div class="reading-stat-card reading-stat-card--daily">
        <div class="reading-stat-accent-bar"></div>
        <div class="reading-stat-body">
          <div class="reading-stat-header">
            <span class="reading-stat-label">日均阅读</span>
          </div>
          <div class="reading-stat-big-number">{{ formatMinutes(stats?.avg_daily_time_seconds || 0) }}</div>
          <div class="reading-stat-detail">分钟</div>
        </div>
      </div>
    </div>

    <div class="calendar-link-row">
      <el-button text type="primary" @click="router.push('/calendar')">
        <el-icon><Calendar /></el-icon>
        查看阅读日历
      </el-button>
    </div>

    <!-- 每日精选论文 -->
    <div class="featured-section">
      <div class="featured-header">
        <h3 class="featured-title">
          <el-icon :size="18"><Reading /></el-icon>
          每日精选论文
        </h3>
        <span class="featured-source">数据来源：arXiv</span>
      </div>

      <el-skeleton v-if="featuredLoading" :rows="2" animated />

      <div v-else-if="featuredError" class="featured-error">
        <el-alert title="精选论文加载失败" type="info" :closable="false" show-icon />
      </div>

      <div v-else-if="featuredPapers.length === 0" class="featured-empty">
        <el-empty description="暂无精选论文" :image-size="60" />
      </div>

      <div v-else class="featured-list">
        <el-card
          v-for="paper in featuredPapers"
          :key="paper.id"
          class="featured-card"
          shadow="hover"
          @click="openArxivLink(paper.arxiv_url)"
        >
          <div class="featured-card-top">
            <el-tag size="small" effect="plain" class="featured-category-tag">{{ paper.category }}</el-tag>
            <span class="featured-date">{{ paper.published_date }}</span>
          </div>
          <h4 class="featured-card-title">{{ paper.title }}</h4>
          <p class="featured-card-authors">{{ paper.authors }}</p>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { getReadingStats, type ReadingStats } from '@/api/stats'
import { fetchFeaturedPapers } from '@/api/featured'
import type { FeaturedPaper } from '@/api/featured'
import { Collection, Checked, Clock, Calendar, Reading } from '@element-plus/icons-vue'

const router = useRouter()
const authStore = useAuthStore()

const stats = ref<ReadingStats | null>(null)

const featuredPapers = ref<FeaturedPaper[]>([])
const featuredLoading = ref(false)
const featuredError = ref(false)

const weekDays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']
const today = new Date()
const todayStr = computed(() => {
  return `${today.getFullYear()}年${today.getMonth() + 1}月${today.getDate()}日 ${weekDays[today.getDay()]}`
})

const hours = today.getHours()
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

function formatMinutes(seconds: number): string {
  if (!seconds || seconds <= 0) return '0'
  return Math.round(seconds / 60).toString()
}

function openArxivLink(url: string) {
  window.open(url, '_blank')
}

async function loadStats() {
  try {
    const resp = await getReadingStats()
    stats.value = resp.data.data
  } catch {
    // stats unavailable
  }
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
  loadFeaturedPapers()
})
</script>

<style scoped>
.dashboard {
  padding: 24px 32px;
  max-width: 1400px;
  margin: 0 auto;
}

/* Welcome */
.welcome-section {
  margin-bottom: 24px;
}

.welcome-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 4px 0;
  letter-spacing: -0.3px;
}

.welcome-subtitle {
  font-size: 14px;
  color: var(--text-tertiary);
  margin: 0;
}

/* Stats */
.stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.stat-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  padding: 18px 20px;
  display: flex;
  align-items: center;
  gap: 14px;
  transition: all 0.25s ease;
  position: relative;
  overflow: hidden;
}

.stat-icon {
  width: 42px;
  height: 42px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-icon--total {
  color: #0d9488;
  background: linear-gradient(135deg, #f0fdfa, #ccfbf1);
}

.stat-icon--read {
  color: #059669;
  background: linear-gradient(135deg, #f0fdf4, #bbf7d0);
}

.stat-icon--unread {
  color: #d97706;
  background: linear-gradient(135deg, #fff7ed, #fde68a);
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 2px 0;
  line-height: 1;
}

.stat-label {
  font-size: 12px;
  color: var(--text-tertiary);
  margin: 0;
  font-weight: 500;
}

/* Reading Stats */
.reading-stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 12px;
}

.reading-stat-card {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  transition: all 0.25s ease;
  position: relative;
  overflow: hidden;
}

.reading-stat-accent-bar {
  height: 3px;
  width: 100%;
}

.reading-stat-card--progress {
  background: linear-gradient(180deg, #ffffff 0%, rgba(240, 253, 250, 0.8) 100%);
}
.reading-stat-card--progress .reading-stat-accent-bar {
  background: linear-gradient(90deg, #0d9488, #5eead4);
}

.reading-stat-card--week {
  background: linear-gradient(180deg, #ffffff 0%, rgba(240, 249, 255, 0.8) 100%);
}
.reading-stat-card--week .reading-stat-accent-bar {
  background: linear-gradient(90deg, #0ea5e9, #7dd3fc);
}

.reading-stat-card--month {
  background: linear-gradient(180deg, #ffffff 0%, rgba(245, 243, 255, 0.8) 100%);
}
.reading-stat-card--month .reading-stat-accent-bar {
  background: linear-gradient(90deg, #8b5cf6, #c4b5fd);
}

.reading-stat-card--daily {
  background: linear-gradient(180deg, #ffffff 0%, rgba(255, 251, 235, 0.8) 100%);
}
.reading-stat-card--daily .reading-stat-accent-bar {
  background: linear-gradient(90deg, #f59e0b, #fde68a);
}

.reading-stat-card:hover {
  transform: translateY(-2px);
}
.reading-stat-card--progress:hover {
  border-color: #0d9488;
  background: linear-gradient(180deg, #ffffff 0%, rgba(240, 253, 250, 1) 100%);
  box-shadow: 0 6px 24px rgba(13, 148, 136, 0.12);
}
.reading-stat-card--week:hover {
  border-color: #0ea5e9;
  background: linear-gradient(180deg, #ffffff 0%, rgba(240, 249, 255, 1) 100%);
  box-shadow: 0 6px 24px rgba(14, 165, 233, 0.12);
}
.reading-stat-card--month:hover {
  border-color: #8b5cf6;
  background: linear-gradient(180deg, #ffffff 0%, rgba(245, 243, 255, 1) 100%);
  box-shadow: 0 6px 24px rgba(139, 92, 246, 0.12);
}
.reading-stat-card--daily:hover {
  border-color: #f59e0b;
  background: linear-gradient(180deg, #ffffff 0%, rgba(255, 251, 235, 1) 100%);
  box-shadow: 0 6px 24px rgba(245, 158, 11, 0.12);
}

.reading-stat-body {
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.reading-stat-header {
  width: 100%;
  text-align: center;
}

.reading-stat-label {
  font-size: 12px;
  color: var(--text-tertiary);
  font-weight: 500;
  letter-spacing: 0.3px;
}

.reading-stat-card--progress .reading-stat-label {
  color: #0d9488;
}
.reading-stat-card--week .reading-stat-label {
  color: #0ea5e9;
}
.reading-stat-card--month .reading-stat-label {
  color: #7c3aed;
}
.reading-stat-card--daily .reading-stat-label {
  color: #d97706;
}

.progress-ring-wrapper {
  display: flex;
  justify-content: center;
  padding: 2px 0;
}

.reading-stat-big-number {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1;
  margin-top: 4px;
}

.reading-stat-detail {
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 500;
}

.calendar-link-row {
  margin-bottom: 16px;
}

/* Featured Papers */
.featured-section {
  margin-bottom: 24px;
}

.featured-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.featured-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
  display: flex;
  align-items: center;
  gap: 6px;
}

.featured-source {
  font-size: 12px;
  color: var(--text-muted);
}

.featured-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 12px;
}

.featured-card {
  cursor: pointer;
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  transition: all 0.2s;
}

.featured-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
  border-color: var(--accent-primary);
}

.featured-card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.featured-category-tag {
  font-size: 11px;
}

.featured-date {
  font-size: 11px;
  color: var(--text-muted);
}

.featured-card-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 4px;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.featured-card-authors {
  font-size: 12px;
  color: var(--text-tertiary);
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.featured-error {
  margin-bottom: 12px;
}

.featured-empty {
  padding: 20px 0;
}
</style>
