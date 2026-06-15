<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-header-content">
        <h1 class="page-title">我的文献库</h1>
        <p class="page-subtitle">管理和阅读您的学术资料</p>
      </div>
      <div class="flex items-center gap-2">
        <el-select
          v-model="uploadFolderId"
          placeholder="选择文件夹"
          clearable
          size="default"
          style="width: 160px"
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
          class="hidden"
          @change="onFilesSelected"
        />
        <el-button type="primary" :loading="uploadQueue.isUploading" @click="triggerFileSelect">
          <el-icon><Upload /></el-icon>
          上传文献
          <el-badge
            v-if="uploadQueue.items.length > 0"
            :value="uploadQueue.items.length"
            :max="99"
            class="ml-1_5"
          />
        </el-button>
        <el-button @click="importDialogVisible = true">
          <el-icon><Link /></el-icon>
          导入
        </el-button>
      </div>
    </div>

    <div class="flex gap-6 min-h-0">
      <div class="folder-sidebar">
        <div class="flex items-center gap-2 px-4 pb-3 text-sm font-semibold text-slate-800 border-b border-slate-200">
          <el-icon class="text-sky-600"><FolderOpened /></el-icon>
          <span>文件夹</span>
        </div>
        <div class="flex-1 overflow-y-auto px-2 py-1">
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
              <span class="flex items-center justify-center w-5 h-5 rounded-xs flex-shrink-0 hover:bg-slate-100" @click.stop>
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
        <div class="px-3 py-2 border-t border-slate-200">
          <el-input
            v-if="newFolderInputVisible"
            v-model="newFolderName"
            placeholder="文件夹名"
            size="small"
            @keyup.enter="handleCreateFolder"
            @blur="cancelNewFolder"
            ref="newFolderInputRef"
          />
          <el-button v-else text size="small" class="w-full justify-center text-slate-400 hover:text-sky-600 hover:bg-sky-50 rounded-md py-2" @click="showNewFolderInput">
            <el-icon><Plus /></el-icon>
            新建文件夹
          </el-button>
        </div>
      </div>

      <div class="flex-1 min-w-0">
        <div class="flex gap-3 mb-5">
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

        <div v-loading="literatureStore.loading" class="grid gap-4 mb-6" style="grid-template-columns:repeat(auto-fill,minmax(320px,1fr))">
          <el-card
            v-for="lit in literatureStore.literatures"
            :key="lit.id"
            shadow="hover"
            class="cursor-pointer"
            @click="handleCardClick(lit)"
          >
            <div class="flex items-start justify-between mb-2_5 flex-wrap gap-1">
              <div class="card-icon">
                <el-icon :size="20"><Document /></el-icon>
              </div>
              <div class="flex items-center gap-2">
                <el-tag :type="statusType(lit.status)" size="small" effect="plain">{{ statusText(lit.status) }}</el-tag>
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
              <el-tag
                v-if="isProcessingTitle(lit)"
                type="warning"
                size="small"
                effect="dark"
                class="ml-auto"
              >
                <el-icon class="is-loading"><Loading /></el-icon>
                处理中
              </el-tag>
            </div>
            <h3 class="card-title">{{ lit.title || '未识别标题' }}</h3>
            <p class="card-authors">{{ lit.authors || '未知作者' }}</p>
            <div class="flex gap-3 mb-3 text-xs text-slate-400">
              <span v-if="lit.journal">{{ lit.journal }}</span>
              <span v-if="lit.year">{{ lit.year }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-xs text-slate-400 whitespace-nowrap">{{ formatDateOnly(lit.created_at) }}</span>
              <div class="flex items-center gap-2">
                <el-button size="small" type="primary" text @click.stop="openDetail(lit.id)">
                  <el-icon><Reading /></el-icon>
                  详情
                </el-button>
                <el-button size="small" text @click.stop="handleCopyCitation(lit.id)" title="复制 BibTeX 引用">
                  <el-icon><Link /></el-icon>
                </el-button>
                <el-dropdown trigger="click" @click.stop>
                  <el-button size="small" text @click.stop>
                    <el-icon><Folder /></el-icon>
                    <el-icon style="font-size:10px;color:var(--text-muted)"><ArrowDown /></el-icon>
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
      <div v-if="currentLit">
        <h3 class="mt-0">{{ currentLit.title || '未识别标题' }}</h3>
        <p><strong>作者：</strong>{{ currentLit.authors || '-' }}</p>
        <p><strong>期刊：</strong>{{ currentLit.journal || '-' }}</p>
        <p><strong>年份：</strong>{{ currentLit.year || '-' }}</p>
        <p><strong>DOI：</strong>{{ currentLit.doi || '-' }}</p>
        <p><strong>阅读状态：</strong>
          <el-tag :type="statusType(currentLit.status)">{{ statusText(currentLit.status) }}</el-tag>
        </p>
        <el-divider />
        <p><strong>摘要：</strong></p>
        <p class="whitespace-pre-wrap leading-relaxed text-slate-600">{{ currentLit.abstract || '暂无摘要' }}</p>
      </div>
    </el-drawer>

    <el-dialog v-model="renameFolderVisible" title="重命名文件夹" width="360px">
      <el-input v-model="renameFolderName" placeholder="输入新名称" @keyup.enter="confirmRenameFolder" />
      <template #footer>
        <el-button @click="renameFolderVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmRenameFolder">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="importDialogVisible" title="导入文献" width="420px">
      <el-form label-position="top">
        <el-form-item label="DOI">
          <el-input v-model="importDoiValue" placeholder="例：10.1038/s41586-023-06014-9">
            <template #append>
              <el-button :loading="importingDoi" @click="handleImportByDoi">导入</el-button>
            </template>
          </el-input>
        </el-form-item>
        <el-divider />
        <el-form-item label="arXiv ID">
          <el-input v-model="importArxivValue" placeholder="例：2303.08774">
            <template #append>
              <el-button :loading="importingArxiv" @click="handleImportByArxiv">导入</el-button>
            </template>
          </el-input>
        </el-form-item>
      </el-form>
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
  Upload, Document, Reading, Search, Collection,
  Delete, Folder, FolderOpened, FolderDelete,
  Plus, Edit, MoreFilled, ArrowDown, Loading, Link,
} from '@element-plus/icons-vue'
import { useLiteratureStore } from '@/stores/literature'
import { useRouter } from 'vue-router'
import type { Literature } from '@/api/literature'
import { deleteLiterature, updateLiteratureFolder, getLiteratures, importByDoi, importByArxiv, getCitation } from '@/api/literature'
import { getFolders, createFolder, renameFolder, deleteFolder, type FolderItem } from '@/api/folder'
import { getStorage } from '@/api/storage'
import { useUploadQueue } from '@/composables/useUploadQueue'
import UploadProgressPanel from '@/components/business/UploadProgressPanel.vue'
import { formatDateOnly } from '@/utils/time'

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

const folders = ref<FolderItem[]>([])
const selectedFolderId = ref<string | null>(null)
const allLiteratureCount = ref(0)

const newFolderInputVisible = ref(false)
const newFolderName = ref('')
const newFolderInputRef = ref()

// 导入对话框
const importDialogVisible = ref(false)
const importDoiValue = ref('')
const importArxivValue = ref('')
const importingDoi = ref(false)
const importingArxiv = ref(false)

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

onMounted(() => {
  loadFolders()
  handleSearch()
  loadAllCount()
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
      loadAllCount()
      for (const item of newSuccess) {
        notifiedUploadIds.add(item.id)
      }
    }

    for (const item of processingItems) {
      const startTime = processingLiteratureIds.get(item.id)
      if (startTime && Date.now() - startTime > 30000) {
        processingLiteratureIds.delete(item.id)
        const expired = new Set(JSON.parse(sessionStorage.getItem('lit_expired') || '[]'))
        expired.add(item.id)
        sessionStorage.setItem('lit_expired', JSON.stringify([...expired]))
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

async function onFilesSelected(event: Event) {
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

  const totalUploadSize = toAdd.reduce((sum, f) => sum + f.size, 0)
  try {
    const storage = await getStorage()
    if (totalUploadSize > storage.remaining_space) {
      const neededMB = (totalUploadSize / 1024 / 1024).toFixed(2)
      const remainingMB = (storage.remaining_space / 1024 / 1024).toFixed(2)
      const shortfallMB = ((totalUploadSize - storage.remaining_space) / 1024 / 1024).toFixed(2)
      await ElMessageBox.alert(
        `<div style="line-height:1.8">
          <p style="margin:0 0 12px;font-size:14px;color:#1e293b">
            您的存储空间不足，无法完成上传。
          </p>
          <div style="background:#f8fafc;border-radius:8px;padding:12px 16px;margin-bottom:12px">
            <p style="margin:0 0 6px;font-size:13px;color:#64748b">待上传文件大小：<b style="color:#0f172a">${neededMB} MB</b></p>
            <p style="margin:0 0 6px;font-size:13px;color:#64748b">当前剩余空间：<b style="color:#0f172a">${remainingMB} MB</b></p>
            <p style="margin:0;font-size:13px;color:#64748b">空间缺口：<b style="color:#dc2626">${shortfallMB} MB</b></p>
          </div>
          <p style="margin:0 0 8px;font-size:13px;color:#475569;font-weight:600">您可以尝试以下方式解决：</p>
          <ul style="margin:0;padding:0 0 0 18px;font-size:13px;color:#475569;line-height:2">
            <li>删除以前上传的文献以释放空间</li>
            <li>通过完成每日打卡等任务获取额外存储空间</li>
            <li>通过充值购买更多存储空间（即将上线）</li>
          </ul>
        </div>`,
        '存储空间不足',
        {
          confirmButtonText: '我知道了',
          type: 'warning',
          dangerouslyUseHTMLString: true,
          customClass: 'storage-insufficient-dialog',
        },
      )
      input.value = ''
      return
    }
  } catch (err: unknown) {
    if (err === 'cancel' || (err instanceof Error && err.message === 'cancel')) {
      input.value = ''
      return
    }
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
    const resp = await getLiteratures({ limit: 1, folder_id: undefined })
    allLiteratureCount.value = resp.data.total
  } catch {
    allLiteratureCount.value = 0
  }
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

function handleCardClick(lit: Literature) {
  if (lit.file_path) {
    router.push(`/read/${lit.id}`)
  } else {
    openDetail(lit.id)
  }
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
  const expired = new Set(JSON.parse(sessionStorage.getItem('lit_expired') || '[]'))
  if (expired.has(lit.id)) return false
  const startTime = processingLiteratureIds.get(lit.id)
  return !(startTime && Date.now() - startTime > 30000)
}

function statusText(status: string) {
  const map: Record<string, string> = {
    unread: '未读',
    reading: '在读',
    read: '已读',
  }
  return map[status] || status
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

async function handleImportByDoi() {
  const doi = importDoiValue.value.trim()
  if (!doi) {
    ElMessage.warning('请输入 DOI')
    return
  }
  importingDoi.value = true
  try {
    await importByDoi(doi)
    ElMessage.success('文献已通过 DOI 导入')
    importDialogVisible.value = false
    importDoiValue.value = ''
    handleSearch()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || 'DOI 导入失败')
  } finally {
    importingDoi.value = false
  }
}

async function handleImportByArxiv() {
  const arxivId = importArxivValue.value.trim()
  if (!arxivId) {
    ElMessage.warning('请输入 arXiv ID')
    return
  }
  importingArxiv.value = true
  try {
    await importByArxiv(arxivId)
    ElMessage.success('文献已通过 arXiv 导入')
    importDialogVisible.value = false
    importArxivValue.value = ''
    handleSearch()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || 'arXiv 导入失败')
  } finally {
    importingArxiv.value = false
  }
}

async function handleCopyCitation(id: string) {
  try {
    const resp = await getCitation(id)
    const citation = resp.data.data.citation
    await navigator.clipboard.writeText(citation)
    ElMessage.success('BibTeX 引用已复制')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '获取引用失败')
  }
}
</script>

<style scoped>
/* ── 贴近左侧侧边栏 ── */
.page-container {
  padding-left: 20px;
  margin-left: 0;
}

/* ── Folder sidebar ── */
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
.folder-item:hover { background: var(--bg-tertiary); }
.folder-item.active {
  background: var(--sky-50);
  color: var(--accent-primary);
  font-weight: 600;
}
.folder-item .el-icon { font-size: 15px; flex-shrink: 0; }

.folder-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.folder-count {
  font-size: 11px;
  color: var(--text-muted);
  background: var(--bg-tertiary);
  padding: 1px 8px;
  border-radius: 10px;
  flex-shrink: 0;
}

/* ── Card icon ── */
.card-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--sky-50);
  border-radius: var(--radius-md);
  color: var(--accent-primary);
}

/* ── Card title with line-clamp ── */
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

/* ── Processing animation (仅限标签内的图标，不波及 el-button) ── */
.el-icon.is-loading {
  animation: spin 1.5s linear infinite;
  margin-right: 2px;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* ── Filters ── */
.search-input { width: 320px; }
.search-input :deep(.el-input__wrapper) {
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
}
.filter-select { width: 140px; }
.filter-select :deep(.el-input__wrapper) { border-radius: var(--radius-lg); }

/* ── Small status select ── */
.status-select { width: 80px; }
.status-select :deep(.el-input__wrapper) { border-radius: var(--radius-md); }

/* ── Mobile responsive ── */
@media (max-width: 768px) {
  .folder-sidebar { display: none; }
  .search-input { width: 100%; }
  .filter-select { flex: 1; min-width: 0; }
}
</style>
