<template>
  <div class="mx-auto" style="max-width:1100px;padding:32px">
    <div class="presentation-header">
      <div class="section-bar">
        <div class="section-bar-line"></div>
        <h1 class="section-title">组会看板</h1>
        <span class="section-accent">PRESENTATION</span>
      </div>
      <p class="section-subtitle">选择论文，一键生成专业学术 PPT</p>
    </div>

    <div class="flex items-center justify-between gap-6 p-7 mb-6 rounded-2xl border" style="background:linear-gradient(135deg,var(--sky-50),#ecfdf5);border-color:var(--sky-200)">
      <div class="flex items-center gap-4">
        <div class="w-14 h-14 rounded-xl bg-sky-100 text-sky-600 flex items-center justify-center flex-shrink-0">
          <el-icon :size="28"><DataAnalysis /></el-icon>
        </div>
        <div>
          <h3 class="text-lg font-bold text-slate-800 m-0 mb-1">准备新汇报</h3>
          <p class="text-xs text-slate-400 m-0">选择论文后点击生成，稍等片刻即可预览和下载</p>
        </div>
      </div>
      <div class="flex items-center gap-2 flex-shrink-0 flex-wrap">
        <el-select
          v-model="selectedLiteratureId"
          placeholder="选择文献..."
          filterable
          clearable
          style="width:240px"
        >
          <el-option
            v-for="lit in literatureOptions"
            :key="lit.id"
            :label="lit.title || '未识别标题'"
            :value="lit.id"
          >
            <span>{{ lit.title || '未识别标题' }}</span>
            <span style="font-size:12px;color:var(--text-muted);margin-left:8px">{{ lit.authors }}</span>
          </el-option>
        </el-select>
        <el-button type="primary" :loading="generating" :disabled="!selectedLiteratureId" @click="handleGeneratePPT">
          <el-icon><MagicStick /></el-icon>
          生成汇报 PPT
        </el-button>
      </div>
    </div>

    <div v-if="generating" class="flex items-center gap-2_5 px-5 py-3_5 mb-6 bg-white border border-slate-200 rounded-lg text-sm text-slate-600">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>{{ progressMessage }}</span>
    </div>

    <div v-if="lastResult" class="bg-white border border-sky-200 rounded-2xl p-5 px-6 mb-8">
      <div class="flex items-center gap-2 text-sm font-semibold text-sky-700 mb-3">
        <el-icon :size="20"><CircleCheck /></el-icon>
        <span>PPT 已生成，共 {{ lastResult.slides?.length || 0 }} 页</span>
      </div>
      <div class="flex flex-wrap gap-2">
        <div
          v-for="(slide, idx) in lastResult.slides.slice(0, 4)"
          :key="idx"
          class="flex items-center gap-1_5 px-3_5 py-1_5 bg-sky-50 rounded-full text-xs text-slate-600 max-w-[280px] truncate"
        >
          <span class="w-5 h-5 rounded-full bg-sky-500 text-white text-[11px] font-bold flex items-center justify-center flex-shrink-0">{{ idx + 1 }}</span>
          <span class="text-[10px] text-sky-600 bg-sky-100 px-1 rounded-xs flex-shrink-0">{{ slide.page_type || 'text' }}</span>
          {{ slide.title }}
        </div>
        <span v-if="lastResult.slides.length > 4" class="flex items-center px-3_5 py-1_5 text-xs text-slate-400">
          +{{ lastResult.slides.length - 4 }} 张
        </span>
        <el-button type="primary" size="small" @click="openPreview(lastResult)" class="ml-auto">
          预览并下载
        </el-button>
      </div>
    </div>

    <div class="mt-2">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-bold text-slate-800 m-0">汇报历史</h2>
        <span class="text-xs text-slate-400">共 {{ presentations.length }} 条记录</span>
      </div>

      <div v-loading="loading" class="flex flex-col gap-4">
        <el-card
          v-for="pres in presentations"
          :key="pres.id"
          shadow="hover"
          class="cursor-pointer"
          @click="openPreviewFromHistory(pres)"
        >
          <div class="flex items-start gap-5">
            <div class="w-12 h-12 rounded-xl bg-sky-50 text-sky-600 flex items-center justify-center flex-shrink-0 mt-0.5">
              <el-icon :size="22"><DataAnalysis /></el-icon>
            </div>
            <div class="flex-1 min-w-0">
              <h4 class="text-base font-semibold text-slate-800 m-0 mb-2 leading-snug">{{ pres.literature_title || '未命名文献' }}</h4>
              <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-400">
                <span class="flex items-center gap-1">
                  <el-icon :size="14"><Collection /></el-icon>
                  {{ pres.slide_count || '0' }} 张幻灯片
                </span>
                <span class="flex items-center gap-1">
                  <el-icon :size="14"><Clock /></el-icon>
                  {{ formatDate(pres.created_at) }}
                </span>
              </div>
            </div>
          </div>
          <div class="flex gap-2 mt-4 pt-4 border-t border-slate-100" @click.stop>
            <el-button text type="primary" size="small"><el-icon><View /></el-icon>预览</el-button>
            <el-button text type="danger" size="small" @click="handleDelete(pres)"><el-icon><Delete /></el-icon>删除</el-button>
          </div>
        </el-card>

        <el-empty v-if="!loading && presentations.length === 0" description="暂无汇报记录" />
      </div>
    </div>

    <el-dialog v-model="previewVisible" :title="previewTitle" fullscreen :close-on-click-modal="false" destroy-on-close>
      <div v-if="previewSlides.length > 0" class="py-4">
        <div class="grid gap-5" style="grid-template-columns:repeat(auto-fill,minmax(340px,1fr))">
          <div v-for="(slide, idx) in previewSlides" :key="idx" class="preview-slide-card">
            <div class="flex items-start gap-3 mb-4">
              <span class="w-7 h-7 rounded-md bg-sky-600 text-white text-xs font-bold flex items-center justify-center flex-shrink-0">{{ idx + 1 }}</span>
              <span class="text-base font-bold text-slate-800 leading-tight flex-1">{{ slide.title }}</span>
              <el-tag v-if="slide.page_type" size="small" class="flex-shrink-0 mt-0_5">{{ slide.page_type }}</el-tag>
            </div>
            <ul class="m-0 p-0 pl-5 list-none">
              <li v-for="(bullet, bi) in slide.bullets" :key="bi" class="relative text-xs leading-relaxed text-slate-600 py-0_5" style="padding-left:16px">
                <span class="absolute left-[-16px] top-[10px] w-[5px] h-[5px] rounded-full bg-sky-400"></span>
                {{ bullet }}
              </li>
            </ul>
            <div v-if="slide.notes || slide.speaker_notes" class="flex items-start gap-1_5 mt-3_5 pt-3_5 border-t border-dashed border-slate-200 text-xs text-slate-400 leading-relaxed">
              <el-icon><ChatLineSquare /></el-icon>
              <span>{{ slide.notes || slide.speaker_notes }}</span>
            </div>
          </div>
        </div>
      </div>
      <el-empty v-else description="暂无幻灯片" />

      <template #footer>
        <div class="flex items-center justify-between w-full">
          <span class="text-xs text-slate-600">共 {{ previewSlides.length }} 页</span>
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
import { DataAnalysis, MagicStick, Loading, CircleCheck, ChatLineSquare, Download, View, Collection, Clock, Delete } from '@element-plus/icons-vue'
import { getPresentations, deletePresentation, type PresentationItem } from '@/api/presentation'
import { getLiteratures, type Literature } from '@/api/literature'
import { startPPTGeneration, getPPTStatus, downloadPPT, type SlideData, type PPTTaskResponse } from '@/api/outline'
import { formatDateTime } from '@/utils/time'

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

const formatDate = formatDateTime

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
.presentation-header {
  margin-bottom: 24px;
}

.section-bar {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 6px;
}

.section-bar-line {
  width: 4px;
  height: 22px;
  border-radius: 3px;
  background: linear-gradient(180deg, var(--accent-primary) 0%, var(--sky-400) 100%);
  flex-shrink: 0;
}

.section-title {
  font-size: 22px;
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

.section-subtitle {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
  margin: 0 0 0 18px;
  letter-spacing: 0.01em;
}

/* ── Preview slide card ── */
.preview-slide-card {
  background: rgba(255, 255, 255, 0.55);
  border: 1px solid rgba(226, 232, 240, 0.4);
  border-radius: var(--radius-xl);
  padding: 24px;
  min-height: 180px;
  backdrop-filter: blur(4px);
}

/* ── History card spacing ── */
.el-card :deep(.el-card__body) {
  padding: 20px;
}
</style>
