<template>
  <div class="admin-statistics">
    <h2 class="page-title">数据统计</h2>

    <div class="period-switch">
      <el-radio-group v-model="period" @change="loadTimeseries">
        <el-radio-button value="day">近30天</el-radio-button>
        <el-radio-button value="week">近12周</el-radio-button>
        <el-radio-button value="month">近12月</el-radio-button>
        <el-radio-button value="year">近3年</el-radio-button>
      </el-radio-group>
    </div>

    <div class="overview-cards">
      <div class="stat-card total">
        <div class="stat-card-icon"><el-icon :size="24"><UserFilled /></el-icon></div>
        <div class="stat-card-body">
          <p class="stat-card-value">{{ overview?.total_users ?? '-' }}</p>
          <p class="stat-card-label">用户总数</p>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-card-icon"><el-icon :size="24"><Document /></el-icon></div>
        <div class="stat-card-body">
          <p class="stat-card-value">{{ overview?.total_literatures ?? '-' }}</p>
          <p class="stat-card-label">文献总数</p>
        </div>
      </div>
      <div class="stat-card success">
        <div class="stat-card-icon"><el-icon :size="24"><Checked /></el-icon></div>
        <div class="stat-card-body">
          <p class="stat-card-value">{{ overview?.total_read_literatures ?? '-' }}</p>
          <p class="stat-card-label">已读文献</p>
        </div>
      </div>
      <div class="stat-card warning">
        <div class="stat-card-icon"><el-icon :size="24"><Clock /></el-icon></div>
        <div class="stat-card-body">
          <p class="stat-card-value">{{ overview?.total_unread_literatures ?? '-' }}</p>
          <p class="stat-card-label">未读文献</p>
        </div>
      </div>
      <div class="stat-card info">
        <div class="stat-card-icon"><el-icon :size="24"><Notebook /></el-icon></div>
        <div class="stat-card-body">
          <p class="stat-card-value">{{ overview?.total_notes ?? '-' }}</p>
          <p class="stat-card-label">笔记总数</p>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-card-icon"><el-icon :size="24"><DataAnalysis /></el-icon></div>
        <div class="stat-card-body">
          <p class="stat-card-value">{{ overview?.total_presentations ?? '-' }}</p>
          <p class="stat-card-label">组会总数</p>
        </div>
      </div>
    </div>

    <div class="chart-section" v-loading="chartLoading">
      <h3 class="section-title">新增用户趋势</h3>
      <div class="bar-chart" v-if="tsData?.new_users?.length">
        <div
          v-for="(point, idx) in tsData.new_users"
          :key="idx"
          class="bar-item"
        >
          <div
            class="bar-fill"
            :style="{ height: barHeight(point.value, maxUserVal) }"
            :title="`${point.date}: ${point.value}`"
          ></div>
          <span class="bar-label">{{ formatDate(point.date) }}</span>
          <span class="bar-val">{{ point.value }}</span>
        </div>
      </div>
      <el-empty v-else description="暂无数据" :image-size="40" />

      <h3 class="section-title">新增文献趋势</h3>
      <div class="bar-chart" v-if="tsData?.new_literatures?.length">
        <div
          v-for="(point, idx) in tsData.new_literatures"
          :key="idx"
          class="bar-item"
        >
          <div
            class="bar-fill"
            :style="{ height: barHeight(point.value, maxLitVal) }"
            :title="`${point.date}: ${point.value}`"
          ></div>
          <span class="bar-label">{{ formatDate(point.date) }}</span>
          <span class="bar-val">{{ point.value }}</span>
        </div>
      </div>
      <el-empty v-else description="暂无数据" :image-size="40" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  UserFilled, Document, Checked, Clock, Notebook, DataAnalysis,
} from '@element-plus/icons-vue'
import { getStatsOverview, getStatsTimeseries, type StatsOverview, type TimeSeriesStats } from '@/api/admin'

const overview = ref<StatsOverview | null>(null)
const tsData = ref<TimeSeriesStats | null>(null)
const period = ref('day')
const chartLoading = ref(false)

const maxUserVal = computed(() => {
  if (!tsData.value?.new_users?.length) return 1
  return Math.max(...tsData.value.new_users.map(p => p.value), 1)
})

const maxLitVal = computed(() => {
  if (!tsData.value?.new_literatures?.length) return 1
  return Math.max(...tsData.value.new_literatures.map(p => p.value), 1)
})

function barHeight(val: number, max: number): string {
  return Math.max((val / max) * 200, 4) + 'px'
}

function formatDate(dateStr: string): string {
  if (dateStr.length > 10) return dateStr.slice(5, 10)
  return dateStr
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
  } catch { /* handled silently */ }
  finally { chartLoading.value = false }
}

onMounted(() => {
  loadOverview()
  loadTimeseries()
})
</script>

<style scoped>
.admin-statistics {
  max-width: 1200px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 20px 0;
}

.period-switch {
  margin-bottom: 24px;
}

.overview-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 32px;
}

.stat-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 14px;
}

.stat-card-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-secondary);
  color: var(--text-secondary);
  flex-shrink: 0;
}

.stat-card.total .stat-card-icon { background: #ecfeff; color: #0e7490; }
.stat-card.success .stat-card-icon { background: #f0fdf4; color: #16a34a; }
.stat-card.warning .stat-card-icon { background: #fff7ed; color: #ea580c; }
.stat-card.info .stat-card-icon { background: #eff6ff; color: #2563eb; }

.stat-card-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  line-height: 1.1;
}

.stat-card-label {
  font-size: 13px;
  color: var(--text-muted);
  margin: 4px 0 0 0;
}

.chart-section {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 24px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 16px 0;
}

.section-title + .section-title {
  margin-top: 28px;
}

.bar-chart {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 240px;
  overflow-x: auto;
  padding-bottom: 8px;
}

.bar-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 30px;
  flex: 1;
  height: 100%;
  justify-content: flex-end;
}

.bar-fill {
  width: 100%;
  max-width: 40px;
  background: linear-gradient(180deg, var(--accent-primary), #5eead4);
  border-radius: 4px 4px 0 0;
  min-height: 4px;
  transition: height 0.3s ease;
  cursor: pointer;
}

.bar-fill:hover {
  opacity: 0.75;
}

.bar-label {
  font-size: 10px;
  color: var(--text-muted);
  margin-top: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 60px;
}

.bar-val {
  font-size: 10px;
  color: var(--text-tertiary);
}
</style>
