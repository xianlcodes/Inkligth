<template>
  <div class="literature-list-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">我的文献库</h1>
        <p class="page-subtitle">管理和阅读您的学术资料</p>
      </div>
      <div class="header-upload">
        <el-select
          v-model="uploadFolderId"
          placeholder="选择文件夹"
          clearable
          size="default"
          style="width: 160px; margin-right: 8px"
        >
          <el-option label="无文件夹" value="" />
          <el-option
            v-for="f in folders"
            :key="f.id"
            :label="f.name"
            :value="f.id"
          />
        </el-select>
        <input
          ref="fileInputRef"
          type="file"
          accept=".pdf"
          multiple
          style="display: none"
          @change="onFilesSelected"
        />
        <el-button type="primary" :loading="uploadQueue.isUploading" class="upload-btn" @click="triggerFileSelect">
          <el-icon><Upload /></el-icon>
          上传文献
          <el-badge
            v-if="uploadQueue.items.length > 0"
            :value="uploadQueue.items.length"
            :max="99"
            class="upload-badge"
          />
        </el-button>
      </div>
    </div>

    <div class="main-layout">
      <div class="folder-sidebar">
        <div class="folder-sidebar-header">
          <el-icon><FolderOpened /></el-icon>
          <span>文件夹</span>
        </div>
        <div class="folder-list">
          <div
            class="folder-item"
            :class="{ active: selectedFolderId === null }"
            @click="selectFolder(null)"
          >
            <el-icon><Document /></el-icon>
            <span class="folder-name">所有文献</span>
            <span class="folder-count">{{ allLiteratureCount }}</span>
          </div>
          <div
            class="folder-item"
            :class="{ active: selectedFolderId === '__none__' }"
            @click="selectFolder('__none__')"
          >
            <el-icon><FolderDelete /></el-icon>
            <span class="folder-name">未分类</span>
            <span class="folder-count">-</span>
          </div>
          <div
            v-for="f in folders"
            :key="f.id"
            class="folder-item"
            :class="{ active: selectedFolderId === f.id }"
            @click="selectFolder(f.id)"
          >
            <el-icon><Folder /></el-icon>
            <span class="folder-name">{{ f.name }}</span>
            <el-dropdown trigger="click" @click.stop>
              <span class="folder-actions-trigger" @click.stop>
                <el-icon><MoreFilled /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="startRenameFolder(f)">
                    <el-icon><Edit /></el-icon>
                    重命名
                  </el-dropdown-item>
                  <el-dropdown-item @click="handleDeleteFolder(f.id)" style="color: var(--el-color-danger)">
                    <el-icon><Delete /></el-icon>
                    删除
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <span class="folder-count">{{ f.literature_count }}</span>
          </div>
        </div>
        <div class="folder-sidebar-footer">
          <el-input
            v-if="newFolderInputVisible"
            v-model="newFolderName"
            placeholder="文件夹名"
            size="small"
            @keyup.enter="handleCreateFolder"
            @blur="cancelNewFolder"
            ref="newFolderInputRef"
          />
          <el-button v-else text size="small" class="new-folder-btn" @click="showNewFolderInput">
            <el-icon><Plus /></el-icon>
            新建文件夹
          </el-button>
        </div>
      </div>

      <div class="content-area">
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
            @click="openReader(lit.id)"
          >
            <div class="card-top">
              <div class="card-icon">
                <el-icon :size="20"><Document /></el-icon>
              </div>
              <el-tag :type="statusType(lit.status)" size="small" effect="plain">{{ statusText(lit.status) }}</el-tag>
              <el-tag
                v-if="isProcessingTitle(lit)"
                type="warning"
                size="small"
                effect="dark"
                class="processing-tag"
              >
                <el-icon class="is-loading"><Loading /></el-icon>
                处理中
              </el-tag>
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
                <el-button size="small" type="primary" text @click.stop="openDetail(lit.id)">
                  <el-icon><Reading /></el-icon>
                  详情
                </el-button>
                <el-dropdown trigger="click" @click.stop>
                  <el-button size="small" text @click.stop>
                    <el-icon><Folder /></el-icon>
                    <el-icon class="dropdown-arrow"><ArrowDown /></el-icon>
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item
                        v-for="f in moveFolderOptions"
                        :key="f.value"
                        @click="handleMoveToFolder(lit.id, f.value)"
                      >
                        {{ f.label }}
                      </el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
                <el-popconfirm
                  title="确定要删除该文献吗？此操作不可恢复"
                  confirm-button-text="删除"
                  cancel-button-text="取消"
                  @confirm="handleDelete(lit.id)"
                  @click.stop
                >
                  <template #reference>
                    <el-button size="small" type="danger" text @click.stop>
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </template>
                </el-popconfirm>
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
      </div>
    </div>

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

    <el-dialog v-model="renameFolderVisible" title="重命名文件夹" width="360px">
      <el-input v-model="renameFolderName" placeholder="输入新名称" @keyup.enter="confirmRenameFolder" />
      <template #footer>
        <el-button @click="renameFolderVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmRenameFolder">确定</el-button>
      </template>
    </el-dialog>

    <UploadProgressPanel
      :items="uploadQueue.items"
      @pause="uploadQueue.pauseItem"
      @resume="uploadQueue.resumeItem"
      @retry="uploadQueue.retryItem"
      @remove="uploadQueue.removeItem"
      @clear-completed="uploadQueue.clearCompleted"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Upload, Document, Reading, Search, Collection, Checked,
  Clock, Calendar, Delete, Folder, FolderOpened, FolderDelete,
  Plus, Edit, MoreFilled, ArrowDown, Loading,
} from '@element-plus/icons-vue'
import { useLiteratureStore } from '@/stores/literature'
import { useRouter } from 'vue-router'
import type { Literature } from '@/api/literature'
import { deleteLiterature, updateLiteratureFolder } from '@/api/literature'
import { getReadingStats, type ReadingStats } from '@/api/stats'
import { getFolders, createFolder, renameFolder, deleteFolder, type FolderItem } from '@/api/folder'
import { useUploadQueue } from '@/composables/useUploadQueue'
import UploadProgressPanel from '@/components/business/UploadProgressPanel.vue'

const literatureStore = useLiteratureStore()
const router = useRouter()
const uploadQueue = useUploadQueue()
const fileInputRef = ref<HTMLInputElement>()
const uploadFolderId = ref('')
const searchTitle = ref('')
const filterStatus = ref('')
const sortYear = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const drawerVisible = ref(false)
const currentLit = ref<Literature | null>(null)
const readingStats = ref<ReadingStats | null>(null)

const folders = ref<FolderItem[]>([])
const selectedFolderId = ref<string | null>(null)
const allLiteratureCount = ref(0)

const newFolderInputVisible = ref(false)
const newFolderName = ref('')
const newFolderInputRef = ref()

const renameFolderVisible = ref(false)
const renameFolderId = ref<string | null>(null)
const renameFolderName = ref('')

const moveFolderOptions = computed(() => {
  const options: { label: string; value: string | null }[] = [
    { label: '无文件夹', value: null as any },
  ]
  folders.value.forEach(f => {
    options.push({ label: f.name, value: f.id })
  })
  return options
})

const stats = computed(() => [
  { label: '全部文献', value: allLiteratureCount.value, icon: Collection, bg: '#f0fdfa' },
  { label: '已读', value: literatureStore.literatures.filter(p => p.status === 'read').length, icon: Checked, bg: '#f0fdf4' },
  { label: '未读', value: literatureStore.literatures.filter(p => p.status === 'unread').length, icon: Clock, bg: '#fff7ed' },
])

onMounted(() => {
  loadFolders()
  handleSearch()
  fetchReadingStats()
})

let pollTimer: ReturnType<typeof setInterval> | null = null
const processingLiteratureIds = new Map<string, number>()
const notifiedUploadIds = new Set<string>()

onMounted(() => {
  pollTimer = setInterval(async () => {
    const processingItems = literatureStore.literatures.filter(
      (item) => isProcessingTitle(item),
    )

    const newSuccess = uploadQueue.items.filter(
      (item) => item.status === 'success' && item.literatureId && !notifiedUploadIds.has(item.id),
    )

    if (newSuccess.length > 0 || processingItems.length > 0) {
      loadFolders()
      handleSearch()
      for (const item of newSuccess) {
        notifiedUploadIds.add(item.id)
      }
    }

    for (const item of processingItems) {
      const startTime = processingLiteratureIds.get(item.id)
      if (startTime && Date.now() - startTime > 30000) {
        processingLiteratureIds.delete(item.id)
        continue
      }
      if (!startTime) {
        processingLiteratureIds.set(item.id, Date.now())
      }
    }
  }, 2000)
})

onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
  processingLiteratureIds.clear()
  notifiedUploadIds.clear()
})

function triggerFileSelect() {
  fileInputRef.value?.click()
}

function onFilesSelected(event: Event) {
  const input = event.target as HTMLInputElement
  const files = input.files
  if (!files || files.length === 0) return

  const MAX_SIZE = 50 * 1024 * 1024
  const validFiles: File[] = []

  for (let i = 0; i < files.length; i++) {
    const file = files[i]
    const isPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
    if (!isPdf) {
      ElMessage.warning(`跳过非 PDF 文件: ${file.name}`)
      continue
    }
    if (file.size > MAX_SIZE) {
      ElMessage.warning(`文件过大 (${(file.size / 1024 / 1024).toFixed(1)}MB > 50MB): ${file.name}`)
      continue
    }
    validFiles.push(file)
  }

  if (validFiles.length === 0) {
    input.value = ''
    return
  }

  const remaining = uploadQueue.MAX_BATCH_SIZE - uploadQueue.items.filter(
    (i) => i.status === 'pending' || i.status === 'uploading' || i.status === 'processing',
  ).length

  if (remaining <= 0) {
    ElMessage.warning(`上传队列已满（最多 ${uploadQueue.MAX_BATCH_SIZE} 个任务）`)
    input.value = ''
    return
  }

  const toAdd = validFiles.slice(0, remaining)
  if (toAdd.length < validFiles.length) {
    ElMessage.info(`仅添加前 ${toAdd.length} 个文件（队列最多 ${uploadQueue.MAX_BATCH_SIZE} 个）`)
  }

  uploadQueue.addFiles(toAdd, uploadFolderId.value || undefined)
  uploadQueue.startUpload()
  input.value = ''
}

async function loadFolders() {
  try {
    const resp = await getFolders()
    folders.value = resp.data.items
  } catch {
    folders.value = []
  }
}

async function selectFolder(folderId: string | null) {
  selectedFolderId.value = folderId
  currentPage.value = 1
  literatureStore.query.skip = 0
  literatureStore.query.folder_id = folderId ?? undefined
  literatureStore.query.limit = pageSize.value
  await literatureStore.fetchLiteratures()
  await loadAllCount()
}

async function loadAllCount() {
  try {
    const { getLiteratures } = await import('@/api/literature')
    const resp = await getLiteratures({ limit: 1, folder_id: undefined })
    allLiteratureCount.value = resp.data.total
  } catch {
    allLiteratureCount.value = 0
  }
}

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

async function handleDelete(id: string) {
  try {
    await deleteLiterature(id)
    ElMessage.success('删除成功')
    await loadFolders()
    handleSearch()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '删除失败')
  }
}

async function handleMoveToFolder(literatureId: string, folderId: string | null) {
  try {
    await updateLiteratureFolder(literatureId, folderId)
    ElMessage.success('移动成功')
    await loadFolders()
    handleSearch()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '移动失败')
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

function isProcessingTitle(lit: Literature): boolean {
  if (!lit.title) return false
  if (lit.title === '未识别标题') return false
  if (lit.title.length > 200) return false
  if (lit.authors && lit.abstract) return false
  const extPattern = /\.pdf$/i
  const looksLikeFilename = extPattern.test(lit.title) || lit.title.includes('_') && !lit.title.includes(' ')
  if (!looksLikeFilename) return false
  const startTime = processingLiteratureIds.get(lit.id)
  if (startTime && Date.now() - startTime > 30000) return false
  return true
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

function showNewFolderInput() {
  newFolderInputVisible.value = true
  newFolderName.value = ''
  nextTick(() => {
    newFolderInputRef.value?.focus()
  })
}

function cancelNewFolder() {
  setTimeout(() => {
    newFolderInputVisible.value = false
    newFolderName.value = ''
  }, 100)
}

async function handleCreateFolder() {
  const name = newFolderName.value.trim()
  if (!name) {
    newFolderInputVisible.value = false
    return
  }
  try {
    await createFolder(name)
    ElMessage.success('文件夹已创建')
    newFolderInputVisible.value = false
    newFolderName.value = ''
    await loadFolders()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '创建失败')
  }
}

function startRenameFolder(f: FolderItem) {
  renameFolderId.value = f.id
  renameFolderName.value = f.name
  renameFolderVisible.value = true
}

async function confirmRenameFolder() {
  const name = renameFolderName.value.trim()
  if (!name || !renameFolderId.value) return
  try {
    await renameFolder(renameFolderId.value, name)
    ElMessage.success('重命名成功')
    renameFolderVisible.value = false
    await loadFolders()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '重命名失败')
  }
}

async function handleDeleteFolder(id: string) {
  try {
    await ElMessageBox.confirm(
      '文件夹内的文献不会被删除，但会被移出该文件夹。',
      '删除文件夹',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  try {
    await deleteFolder(id)
    ElMessage.success('文件夹已删除')
    if (selectedFolderId.value === id) {
      selectedFolderId.value = null
      literatureStore.query.folder_id = undefined
      handleSearch()
    }
    await loadFolders()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '删除失败')
  }
}
</script>

<style scoped>
.literature-list-page {
  padding: 24px 32px;
  max-width: 1600px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
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

.header-upload {
  display: flex;
  align-items: center;
}

.upload-btn {
  height: 42px;
  padding: 0 20px;
  font-size: 14px;
}

.upload-badge {
  margin-left: 6px;
}

.main-layout {
  display: flex;
  gap: 0;
  min-height: 0;
}

.folder-sidebar {
  width: 210px;
  flex-shrink: 0;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  padding: 12px 0;
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 160px);
  position: sticky;
  top: 20px;
}

.folder-sidebar-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 16px 12px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-color);
  margin-bottom: 4px;
}

.folder-sidebar-header .el-icon {
  color: var(--accent-primary);
}

.folder-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 8px;
}

.folder-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: 13px;
  color: var(--text-secondary);
  transition: all 0.15s;
}

.folder-item:hover {
  background: var(--bg-tertiary);
}

.folder-item.active {
  background: var(--teal-50);
  color: var(--accent-primary);
  font-weight: 600;
}

.folder-item .el-icon {
  font-size: 15px;
  flex-shrink: 0;
}

.folder-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.folder-actions-trigger {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: var(--radius-sm);
  flex-shrink: 0;
}

.folder-actions-trigger:hover {
  background: var(--bg-tertiary);
}

.folder-count {
  font-size: 11px;
  color: var(--text-muted);
  background: var(--bg-tertiary);
  padding: 1px 8px;
  border-radius: 10px;
  flex-shrink: 0;
}

.folder-sidebar-footer {
  padding: 8px 12px;
  border-top: 1px solid var(--border-color);
}

.new-folder-btn {
  width: 100%;
  justify-content: center;
  color: var(--text-muted);
  border-radius: var(--radius-md);
  padding: 8px 0;
}

.new-folder-btn:hover {
  color: var(--accent-primary);
  background: var(--teal-50);
}

.content-area {
  flex: 1;
  min-width: 0;
  margin-left: 20px;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.stat-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-2xl);
  padding: 16px 20px;
  display: flex;
  align-items: center;
  gap: 14px;
  transition: box-shadow 0.2s;
}

.stat-card:hover {
  box-shadow: var(--shadow-md);
}

.stat-icon {
  width: 42px;
  height: 42px;
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
}

.reading-stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 12px;
}

.reading-stat-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-2xl);
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  transition: box-shadow 0.2s;
}

.reading-stat-card:hover {
  box-shadow: var(--shadow-md);
}

.reading-stat-header {
  width: 100%;
}

.reading-stat-label {
  font-size: 12px;
  color: var(--text-tertiary);
  font-weight: 500;
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
}

.reading-stat-detail {
  font-size: 12px;
  color: var(--text-muted);
}

.calendar-link-row {
  margin-bottom: 16px;
}

.filters {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
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
}

.card-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.literature-card {
  cursor: pointer;
  border-radius: var(--radius-xl);
  border: 1px solid var(--border-color);
  transition: all 0.2s;
}

.literature-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  flex-wrap: wrap;
  gap: 4px;
}

.processing-tag {
  margin-left: auto;
}

.processing-tag .is-loading {
  animation: spin 1.5s linear infinite;
  margin-right: 2px;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.card-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--teal-50);
  border-radius: var(--radius-md);
  color: var(--accent-primary);
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 6px;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-authors {
  font-size: 13px;
  color: var(--text-tertiary);
  margin: 0 0 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-meta {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
  font-size: 12px;
  color: var(--text-muted);
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.upload-time {
  font-size: 12px;
  color: var(--text-muted);
}

.card-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.dropdown-arrow {
  font-size: 10px;
  color: var(--text-muted);
}

.status-select {
  width: 80px;
}

.status-select :deep(.el-input__wrapper) {
  border-radius: var(--radius-md);
}

.abstract {
  white-space: pre-wrap;
  line-height: 1.7;
  color: var(--text-secondary);
}

.detail-content h3 {
  margin-top: 0;
}
</style>
