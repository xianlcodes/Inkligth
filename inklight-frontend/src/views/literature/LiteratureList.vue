<template>
  <div class="literature-list">
    <div class="page-header">
      <div>
        <h1 class="page-title">我的文献库</h1>
        <p class="page-subtitle">管理和阅读您的学术资料</p>
      </div>
      <el-upload
        class="upload-demo"
        accept=".pdf"
        :show-file-list="false"
        :before-upload="beforeUpload"
        :http-request="handleUpload"
      >
        <el-button type="primary" :loading="uploading" class="upload-btn">
          <el-icon><Upload /></el-icon>
          上传文献
        </el-button>
      </el-upload>
    </div>

    <div class="stats-row">
      <div v-for="stat in stats" :key="stat.label" class="stat-card">
        <div class="stat-icon" :style="{ background: stat.bg }">
          <el-icon :size="20"><component :is="stat.icon" /></el-icon>
        </div>
        <div class="stat-info">
          <p class="stat-value">{{ stat.value }}</p>
          <p class="stat-label">{{ stat.label }}</p>
        </div>
      </div>
    </div>

    <div class="reading-stats-row" v-if="readingStats">
      <div class="reading-stat-card">
        <div class="reading-stat-header">
          <span class="reading-stat-label">阅读进度</span>
        </div>
        <div class="progress-ring-wrapper">
          <el-progress
            type="circle"
            :percentage="readingStats.read_progress"
            :width="80"
            :stroke-width="8"
            color="var(--accent-primary)"
          />
        </div>
        <div class="reading-stat-detail">
          <span>已读 {{ readingStats.read_count }} / {{ readingStats.total_literatures }} 篇</span>
        </div>
      </div>
      <div class="reading-stat-card">
        <div class="reading-stat-header">
          <span class="reading-stat-label">本周阅读</span>
        </div>
        <div class="reading-stat-big-number">{{ readingStats.week_count }}</div>
        <div class="reading-stat-detail">篇</div>
      </div>
      <div class="reading-stat-card">
        <div class="reading-stat-header">
          <span class="reading-stat-label">本月阅读</span>
        </div>
        <div class="reading-stat-big-number">{{ readingStats.month_count }}</div>
        <div class="reading-stat-detail">篇</div>
      </div>
      <div class="reading-stat-card">
        <div class="reading-stat-header">
          <span class="reading-stat-label">日均阅读</span>
        </div>
        <div class="reading-stat-big-number">{{ formatTime(readingStats.avg_daily_time_seconds) }}</div>
        <div class="reading-stat-detail">分钟</div>
      </div>
    </div>

    <div class="calendar-link-row" v-if="readingStats">
      <el-button text type="primary" @click="router.push('/calendar')">
        <el-icon><Calendar /></el-icon>
        查看阅读日历
      </el-button>
    </div>

    <div class="filters">
      <el-input
        v-model="searchTitle"
        placeholder="搜索文献标题或作者..."
        clearable
        class="search-input"
        @change="handleSearch"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <el-select v-model="filterStatus" placeholder="阅读状态" clearable class="filter-select" @change="handleSearch">
        <el-option label="未读" value="unread" />
        <el-option label="在读" value="reading" />
        <el-option label="已读" value="read" />
      </el-select>
      <el-select v-model="sortYear" placeholder="年份排序" clearable class="filter-select" @change="handleSearch">
        <el-option label="年份升序" value="asc" />
        <el-option label="年份降序" value="desc" />
      </el-select>
    </div>

    <div v-loading="literatureStore.loading" class="card-list">
      <el-card
        v-for="lit in literatureStore.literatures"
        :key="lit.id"
        class="literature-card"
        shadow="hover"
        @click="openDetail(lit.id)"
      >
        <div class="card-top">
          <div class="card-icon">
            <el-icon :size="20"><Document /></el-icon>
          </div>
          <el-tag :type="statusType(lit.status)" size="small" effect="plain">{{ statusText(lit.status) }}</el-tag>
        </div>
        <h3 class="card-title">{{ lit.title || '未识别标题' }}</h3>
        <p class="card-authors">{{ lit.authors || '未知作者' }}</p>
        <div class="card-meta">
          <span v-if="lit.journal" class="meta-item">
            {{ lit.journal }}
          </span>
          <span v-if="lit.year" class="meta-item">
            {{ lit.year }}
          </span>
        </div>
        <div class="card-footer">
          <span class="upload-time">{{ formatDate(lit.created_at) }}</span>
          <div class="card-actions">
            <el-button size="small" type="primary" text @click.stop="openReader(lit.id)">
              <el-icon><Reading /></el-icon>
              阅读
            </el-button>
            <el-select
              v-model="lit.status"
              size="small"
              class="status-select"
              @click.stop
              @change="(val: string) => handleStatusChange(lit.id, val)"
            >
              <el-option label="未读" value="unread" />
              <el-option label="在读" value="reading" />
              <el-option label="已读" value="read" />
            </el-select>
          </div>
        </div>
      </el-card>
    </div>

    <el-pagination
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :total="literatureStore.total"
      layout="total, prev, pager, next"
      @current-change="handlePageChange"
    />

    <el-empty v-if="!literatureStore.loading && literatureStore.literatures.length === 0" description="暂无文献，请上传" />

    <el-drawer v-model="drawerVisible" title="文献详情" size="500px">
      <div v-if="currentLit" class="detail-content">
        <h3>{{ currentLit.title || '未识别标题' }}</h3>
        <p><strong>作者：</strong>{{ currentLit.authors || '-' }}</p>
        <p><strong>期刊：</strong>{{ currentLit.journal || '-' }}</p>
        <p><strong>年份：</strong>{{ currentLit.year || '-' }}</p>
        <p><strong>DOI：</strong>{{ currentLit.doi || '-' }}</p>
        <p><strong>阅读状态：</strong>
          <el-tag :type="statusType(currentLit.status)">{{ statusText(currentLit.status) }}</el-tag>
        </p>
        <el-divider />
        <p><strong>摘要：</strong></p>
        <p class="abstract">{{ currentLit.abstract || '暂无摘要' }}</p>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Upload, Document, Reading, Search, Collection, Checked, Clock, Calendar } from '@element-plus/icons-vue'
import { useLiteratureStore } from '@/stores/literature'
import { useRouter } from 'vue-router'
import type { Literature } from '@/api/literature'
import { getReadingStats, type ReadingStats } from '@/api/stats'

const literatureStore = useLiteratureStore()
const router = useRouter()
const uploading = ref(false)
const searchTitle = ref('')
const filterStatus = ref('')
const sortYear = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const drawerVisible = ref(false)
const currentLit = ref<Literature | null>(null)
const readingStats = ref<ReadingStats | null>(null)

const stats = computed(() => [
  { label: '全部文献', value: literatureStore.total || 0, icon: Collection, bg: '#f0fdfa' },
  { label: '已读', value: literatureStore.literatures.filter(p => p.status === 'read').length, icon: Checked, bg: '#f0fdf4' },
  { label: '未读', value: literatureStore.literatures.filter(p => p.status === 'unread').length, icon: Clock, bg: '#fff7ed' },
])

onMounted(() => {
  handleSearch()
  fetchReadingStats()
})

async function fetchReadingStats() {
  try {
    const resp = await getReadingStats()
    readingStats.value = resp.data.data
  } catch {
    // stats unavailable
  }
}

function formatTime(seconds: number): string {
  if (!seconds || seconds <= 0) return '0'
  return Math.round(seconds / 60).toString()
}

function handleSearch() {
  currentPage.value = 1
  literatureStore.query.title = searchTitle.value || undefined
  literatureStore.query.status = filterStatus.value || undefined
  literatureStore.query.sort_by_year = sortYear.value || undefined
  literatureStore.query.skip = 0
  literatureStore.query.limit = pageSize.value
  literatureStore.fetchLiteratures()
}

function handlePageChange(page: number) {
  currentPage.value = page
  literatureStore.query.skip = (page - 1) * pageSize.value
  literatureStore.fetchLiteratures()
}

function beforeUpload(file: File) {
  const isPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
  if (!isPdf) {
    ElMessage.error('只能上传 PDF 文件')
    return false
  }
  const isLt50M = file.size / 1024 / 1024 < 50
  if (!isLt50M) {
    ElMessage.error('文件大小不能超过 50MB')
    return false
  }
  return true
}

async function handleUpload(options: any) {
  uploading.value = true
  try {
    await literatureStore.upload(options.file)
    ElMessage.success('上传成功')
    handleSearch()
  } catch (error: any) {
    if (error.response?.status === 409) {
      ElMessage.warning('文献已存在')
    } else {
      ElMessage.error(error.response?.data?.detail || '上传失败')
    }
  } finally {
    uploading.value = false
  }
}

async function openDetail(id: string) {
  const lit = await literatureStore.fetchLiteratureDetail(id)
  currentLit.value = lit
  drawerVisible.value = true
}

function openReader(id: string) {
  router.push(`/read/${id}`)
}

async function handleStatusChange(id: string, status: string) {
  try {
    await literatureStore.updateStatus(id, status)
    ElMessage.success('状态更新成功')
  } catch {
    ElMessage.error('状态更新失败')
  }
}

function statusType(status: string) {
  const map: Record<string, string> = {
    unread: 'info',
    reading: 'warning',
    read: 'success',
  }
  return map[status] || 'info'
}

function statusText(status: string) {
  const map: Record<string, string> = {
    unread: '未读',
    reading: '在读',
    read: '已读',
  }
  return map[status] || status
}

function formatDate(dateStr: string) {
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}月${d.getDate()}日`
}
</script>

<style scoped>
.literature-list {
  padding: 32px;
  max-width: 1400px;
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

.upload-btn {
  height: 42px;
  padding: 0 20px;
  font-size: 14px;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-2xl);
  padding: 20px 24px;
  display: flex;
  align-items: center;
  gap: 16px;
  transition: box-shadow 0.2s;
}

.stat-card:hover {
  box-shadow: var(--shadow-md);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--teal-600);
  flex-shrink: 0;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 2px 0;
  line-height: 1;
}

.stat-label {
  font-size: 13px;
  color: var(--text-tertiary);
  margin: 0;
}

.reading-stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.reading-stat-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-2xl);
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  transition: box-shadow 0.2s;
}

.reading-stat-card:hover {
  box-shadow: var(--shadow-md);
}

.reading-stat-header {
  width: 100%;
}

.reading-stat-label {
  font-size: 13px;
  color: var(--text-tertiary);
  font-weight: 500;
}

.progress-ring-wrapper {
  display: flex;
  justify-content: center;
  padding: 4px 0;
}

.reading-stat-big-number {
  font-size: 32px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1;
}

.reading-stat-detail {
  font-size: 12px;
  color: var(--text-muted);
}

.calendar-link-row {
  margin-bottom: 24px;
}

.filters {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.search-input {
  width: 320px;
}

.search-input :deep(.el-input__wrapper) {
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
}

.filter-select {
  width: 140px;
}

.filter-select :deep(.el-input__wrapper) {
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
}

.card-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.literature-card {
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-2xl);
}

.literature-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.08);
  border-color: var(--teal-200);
}

.literature-card :deep(.el-card__body) {
  padding: 20px;
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.card-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  background: var(--teal-50);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--teal-600);
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  line-height: 1.5;
  color: var(--text-primary);
  margin: 0 0 8px 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.literature-card:hover .card-title {
  color: var(--accent-primary);
}

.card-authors {
  font-size: 13px;
  color: var(--text-tertiary);
  margin: 0 0 12px 0;
  line-height: 1.4;
}

.card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.meta-item {
  font-size: 12px;
  color: var(--text-muted);
  background: var(--bg-tertiary);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid var(--border-color);
}

.card-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.upload-time {
  font-size: 12px;
  color: var(--text-muted);
}

.status-select {
  width: 100px;
}

.detail-content h3 {
  margin-top: 0;
  color: var(--text-primary);
}

.detail-content .abstract {
  line-height: 1.7;
  color: var(--text-secondary);
}
</style>
