<template>
  <div class="pre-meeting">
    <div class="page-header">
      <div>
        <h1 class="page-title">组会看板</h1>
        <p class="page-subtitle">选择论文，一键生成专业学术 PPT</p>
      </div>
    </div>

    <div class="new-report-card">
      <div class="new-report-content">
        <div class="new-report-icon">
          <el-icon :size="28"><DataAnalysis /></el-icon>
        </div>
        <div class="new-report-info">
          <h3 class="new-report-title">准备新汇报</h3>
          <p class="new-report-sub">选择论文后点击生成，稍等片刻即可预览和下载</p>
        </div>
      </div>
      <div class="new-report-actions">
        <el-select
          v-model="selectedLiteratureId"
          placeholder="选择文献..."
          filterable
          clearable
          class="literature-select"
        >
          <el-option
            v-for="lit in literatureOptions"
            :key="lit.id"
            :label="lit.title || '未识别标题'"
            :value="lit.id"
          >
            <span>{{ lit.title || '未识别标题' }}</span>
            <span class="lit-option-author">{{ lit.authors }}</span>
          </el-option>
        </el-select>
        <el-button
          type="primary"
          :loading="generating"
          :disabled="!selectedLiteratureId"
          @click="handleGeneratePPT"
        >
          <el-icon><MagicStick /></el-icon>
          生成汇报 PPT
        </el-button>
      </div>
    </div>

    <div v-if="generating" class="generating-bar">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>{{ progressMessage }}</span>
    </div>

    <div v-if="lastResult" class="fresh-outline-card">
      <div class="fresh-outline-header">
        <el-icon :size="20" color="var(--teal-600)"><CircleCheck /></el-icon>
        <span>PPT 已生成，共 {{ lastResult.slides?.length || 0 }} 页</span>
      </div>
      <div class="fresh-outline-preview">
        <div
          v-for="(slide, idx) in lastResult.slides.slice(0, 4)"
          :key="idx"
          class="fresh-slide-chip"
        >
          <span class="fresh-slide-num">{{ idx + 1 }}</span>
          <span class="fresh-slide-type">{{ slide.page_type || 'text' }}</span>
          {{ slide.title }}
        </div>
        <span v-if="lastResult.slides.length > 4" class="fresh-slide-more">
          +{{ lastResult.slides.length - 4 }} 张
        </span>
        <el-button type="primary" size="small" @click="openPreview(lastResult)" style="margin-left: auto">
          预览并下载
        </el-button>
      </div>
    </div>

    <div class="history-section">
      <div class="history-header">
        <h2 class="history-title">汇报历史</h2>
        <span class="history-count">共 {{ presentations.length }} 条记录</span>
      </div>

      <div v-loading="loading" class="history-list">
        <el-card
          v-for="pres in presentations"
          :key="pres.id"
          class="history-card"
          shadow="hover"
          @click="openPreviewFromHistory(pres)"
        >
          <div class="history-card-top">
            <div class="history-card-icon">
              <el-icon :size="20"><DataAnalysis /></el-icon>
            </div>
            <div class="history-card-info">
              <h4 class="history-card-title">{{ pres.literature_title || '未命名文献' }}</h4>
              <p class="history-card-meta">
                {{ pres.slide_count || '0 张幻灯片' }}
                <span class="meta-sep">·</span>
                {{ formatDate(pres.created_at) }}
              </p>
            </div>
          </div>
          <div class="history-card-actions" @click.stop>
            <el-button text type="primary" size="small" @click="openPreviewFromHistory(pres)">预览</el-button>
            <el-button text type="danger" size="small" @click="handleDelete(pres)">删除</el-button>
          </div>
        </el-card>

        <el-empty v-if="!loading && presentations.length === 0" description="暂无汇报记录" />
      </div>
    </div>

    <el-dialog
      v-model="previewVisible"
      :title="previewTitle"
      fullscreen
      :close-on-click-modal="false"
      destroy-on-close
    >
      <div v-if="previewSlides.length > 0" class="preview-body">
        <div class="preview-grid">
          <div
            v-for="(slide, idx) in previewSlides"
            :key="idx"
            class="preview-slide-card"
          >
            <div class="preview-slide-header">
              <span class="preview-slide-num">{{ idx + 1 }}</span>
              <span class="preview-slide-title">{{ slide.title }}</span>
              <el-tag v-if="slide.page_type" size="small" class="slide-type-tag">{{ slide.page_type }}</el-tag>
            </div>
            <ul class="preview-slide-bullets">
              <li v-for="(bullet, bi) in slide.bullets" :key="bi">{{ bullet }}</li>
            </ul>
            <div v-if="slide.notes || slide.speaker_notes" class="preview-slide-notes">
              <el-icon><ChatLineSquare /></el-icon>
              <span>{{ slide.notes || slide.speaker_notes }}</span>
            </div>
          </div>
        </div>
      </div>
      <el-empty v-else description="暂无幻灯片" />

      <template #footer>
        <div class="preview-footer-actions">
          <span class="preview-slide-count">共 {{ previewSlides.length }} 页</span>
          <el-button type="primary" :loading="downloading" @click="handleDownload" :disabled="!previewTaskId">
            <el-icon><Download /></el-icon>
            下载 PPT
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DataAnalysis, MagicStick, Loading, CircleCheck, ChatLineSquare, Download } from '@element-plus/icons-vue'
import { getPresentations, deletePresentation, type PresentationItem } from '@/api/presentation'
import { getLiteratures, type Literature } from '@/api/literature'
import { startPPTGeneration, getPPTStatus, downloadPPT, type SlideData, type PPTTaskResponse } from '@/api/outline'
import { formatDateCN } from '@/utils/date'

const loading = ref(false)
const generating = ref(false)
const downloading = ref(false)
const presentations = ref<PresentationItem[]>([])
const selectedLiteratureId = ref('')
const literatureOptions = ref<Literature[]>([])

const progressMessage = ref('正在准备...')
const lastResult = ref<PPTTaskResponse | null>(null)
const currentTaskId = ref('')

const previewVisible = ref(false)
const previewTitle = ref('')
const previewSlides = ref<SlideData[]>([])
const previewTaskId = ref('')

const formatDate = formatDateCN

onMounted(() => {
  fetchPresentations()
  fetchAllLiterature()
  resumeTaskIfNeeded()
})

async function fetchPresentations() {
  loading.value = true
  try {
    const resp = await getPresentations()
    presentations.value = resp.data.data.items
  } catch {
    presentations.value = []
  } finally {
    loading.value = false
  }
}

async function fetchAllLiterature() {
  try {
    const resp = await getLiteratures({ limit: 100 })
    literatureOptions.value = resp.data.items
  } catch {
    literatureOptions.value = []
  }
}

async function handleGeneratePPT() {
  if (!selectedLiteratureId.value) return

  generating.value = true
  lastResult.value = null
  currentTaskId.value = ''
  progressMessage.value = '正在解析论文并提取图表...'

  try {
    const startResp = await startPPTGeneration(selectedLiteratureId.value)
    const taskId = startResp.data.data.task_id
    currentTaskId.value = taskId
    sessionStorage.setItem('ppt_task_id', taskId)
    sessionStorage.setItem('ppt_literature_id', selectedLiteratureId.value)
    await pollTask(selectedLiteratureId.value, taskId)
  } catch (error: any) {
    console.error('PPT 生成失败:', error)
    ElMessage.error(error?.response?.data?.detail || error?.message || '生成失败')
  } finally {
    generating.value = false
  }
}

async function pollTask(litId: string, taskId: string) {
  while (true) {
    await new Promise(r => setTimeout(r, 1500))
    try {
      const statusResp = await getPPTStatus(litId, taskId)
      const task = statusResp.data

      if (task.status === 'completed') {
        lastResult.value = task
        ElMessage.success(`PPT 生成完成，共 ${task.slides?.length || 0} 页`)
        openPreview(task)
        await fetchPresentations()
        sessionStorage.removeItem('ppt_task_id')
        sessionStorage.removeItem('ppt_literature_id')
        generating.value = false
        return
      }

      if (task.status === 'failed') {
        ElMessage.error(task.error || 'PPT 生成失败')
        sessionStorage.removeItem('ppt_task_id')
        sessionStorage.removeItem('ppt_literature_id')
        generating.value = false
        return
      }

      const pct = task.progress || 0
      if (pct < 20) progressMessage.value = '正在解析论文并提取图表...'
      else if (pct < 70) progressMessage.value = 'AI 正在生成大纲...'
      else if (pct < 90) progressMessage.value = '正在渲染 PPT...'
      else progressMessage.value = '正在保存...'
    } catch (error) {
      // 网络错误等静默重试
      await new Promise(r => setTimeout(r, 2000))
    }
  }
}

function resumeTaskIfNeeded() {
  const savedTaskId = sessionStorage.getItem('ppt_task_id')
  const savedLitId = sessionStorage.getItem('ppt_literature_id')
  if (!savedTaskId || !savedLitId) return

  selectedLiteratureId.value = savedLitId
  currentTaskId.value = savedTaskId
  generating.value = true
  progressMessage.value = '正在恢复任务...'
  pollTask(savedLitId, savedTaskId)
}

function openPreview(result: PPTTaskResponse) {
  const lit = literatureOptions.value.find(l => l.id === selectedLiteratureId.value)
  previewTitle.value = lit?.title || '汇报 PPT'
  previewSlides.value = result.slides || []
  previewTaskId.value = currentTaskId.value
  previewVisible.value = true
}

function openPreviewFromHistory(pres: PresentationItem) {
  previewTitle.value = pres.literature_title || '汇报大纲'
  previewSlides.value = (pres.slides || []) as SlideData[]
  previewTaskId.value = ''  // 历史记录的 PPT 文件可能已不存在
  previewVisible.value = true
}

async function handleDelete(pres: PresentationItem) {
  try {
    await ElMessageBox.confirm('确定删除该汇报记录？', '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }

  try {
    await deletePresentation(pres.id)
    ElMessage.success('已删除')
    await fetchPresentations()
  } catch {
    ElMessage.error('删除失败')
  }
}

async function handleDownload() {
  if (!previewTaskId.value) {
    ElMessage.warning('请先生成 PPT')
    return
  }

  downloading.value = true
  try {
    const resp = await downloadPPT(selectedLiteratureId.value || '', previewTaskId.value)
    const blob = new Blob([resp.data], {
      type: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${previewTitle.value || 'presentation'}.pptx`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    ElMessage.success('下载成功')
  } catch (error: any) {
    console.error('下载失败:', error)
    ElMessage.error(error?.response?.data?.detail || error?.message || '下载失败')
  } finally {
    downloading.value = false
  }
}
</script>

<style scoped>
.pre-meeting {
  padding: 32px;
  max-width: 1100px;
  margin: 0 auto;
}

.page-header {
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

.new-report-card {
  background: linear-gradient(135deg, var(--teal-50) 0%, #ecfdf5 100%);
  border: 1px solid var(--teal-200);
  border-radius: var(--radius-2xl);
  padding: 28px 32px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
  margin-bottom: 24px;
}

.new-report-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.new-report-icon {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-xl);
  background: var(--teal-100);
  color: var(--teal-600);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.new-report-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 4px 0;
}

.new-report-sub {
  font-size: 13px;
  color: var(--text-tertiary);
  margin: 0;
}

.new-report-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  flex-wrap: wrap;
}

.literature-select {
  width: 240px;
}

.lit-option-author {
  font-size: 12px;
  color: var(--text-muted);
  margin-left: 8px;
}

.generating-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 20px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  margin-bottom: 24px;
  font-size: 14px;
  color: var(--text-secondary);
}

.fresh-outline-card {
  background: var(--bg-primary);
  border: 1px solid var(--teal-200);
  border-radius: var(--radius-2xl);
  padding: 20px 24px;
  margin-bottom: 32px;
}

.fresh-outline-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--teal-700);
  margin-bottom: 12px;
}

.fresh-outline-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.fresh-slide-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: var(--teal-50);
  border-radius: 20px;
  font-size: 13px;
  color: var(--text-secondary);
  max-width: 280px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fresh-slide-num {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--teal-500);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.fresh-slide-type {
  font-size: 10px;
  color: var(--teal-600);
  background: var(--teal-100);
  padding: 1px 5px;
  border-radius: 4px;
  flex-shrink: 0;
}

.fresh-slide-more {
  display: flex;
  align-items: center;
  padding: 6px 14px;
  font-size: 13px;
  color: var(--text-muted);
}

.history-section {
  margin-top: 8px;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.history-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.history-count {
  font-size: 13px;
  color: var(--text-muted);
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.history-card {
  cursor: pointer;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  transition: all 0.2s;
}

.history-card:hover {
  border-color: var(--teal-200);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
}

.history-card-top {
  display: flex;
  align-items: center;
  gap: 14px;
}

.history-card-icon {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-lg);
  background: var(--teal-50);
  color: var(--teal-600);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.history-card-info {
  flex: 1;
  min-width: 0;
}

.history-card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 4px 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-card-meta {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0;
}

.meta-sep {
  margin: 0 6px;
}

.history-card-actions {
  display: flex;
  gap: 4px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-light);
}

.preview-body {
  padding: 16px 0;
}

.preview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 20px;
}

.preview-slide-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  padding: 24px;
  min-height: 180px;
}

.preview-slide-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 16px;
}

.preview-slide-num {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-md);
  background: var(--accent-primary);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.preview-slide-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.4;
  flex: 1;
}

.slide-type-tag {
  flex-shrink: 0;
  margin-top: 2px;
}

.preview-slide-bullets {
  margin: 0;
  padding: 0 0 0 20px;
  list-style: none;
}

.preview-slide-bullets li {
  position: relative;
  font-size: 13px;
  line-height: 1.8;
  color: var(--text-secondary);
  padding: 2px 0;
}

.preview-slide-bullets li::before {
  content: '';
  position: absolute;
  left: -16px;
  top: 10px;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--teal-400);
}

.preview-slide-notes {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px dashed var(--border-color);
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.6;
}

.preview-slide-notes .el-icon {
  flex-shrink: 0;
  margin-top: 2px;
}

.preview-footer-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.preview-slide-count {
  font-size: 13px;
  color: var(--text-secondary);
}
</style>
