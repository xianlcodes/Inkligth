<template>
  <el-dialog
    v-model="visible"
    :title="dialogTitle"
    width="480px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    @close="handleDialogClose"
  >
    <div class="pdf-translate-dialog">
      <div v-if="!showProgress" class="config-section">
        <el-form label-position="top" size="default">
          <el-form-item label="源语言">
            <el-select v-model="sourceLang" style="width: 100%">
              <el-option label="English" value="en" />
              <el-option label="简体中文" value="zh" />
              <el-option label="日本語" value="ja" />
              <el-option label="한국어" value="ko" />
            </el-select>
          </el-form-item>

          <el-form-item label="目标语言">
            <el-select v-model="targetLang" style="width: 100%">
              <el-option label="简体中文" value="zh" />
              <el-option label="English" value="en" />
              <el-option label="日本語" value="ja" />
              <el-option label="한국어" value="ko" />
            </el-select>
          </el-form-item>

          <el-form-item label="输出模式">
            <el-radio-group v-model="outputMode">
              <el-radio value="mono">
                <span class="mode-label">仅译文</span>
                <span class="mode-desc">仅输出翻译后的 PDF，不保留原文</span>
              </el-radio>
              <el-radio value="dual">
                <span class="mode-label">双语对照</span>
                <span class="mode-desc">原文和译文各一页，方便对比阅读</span>
              </el-radio>
            </el-radio-group>
          </el-form-item>
        </el-form>

        <el-alert type="info" :closable="false" show-icon class="info-alert">
          <template #title>
            翻译将保留原文的排版、字体和图片，仅替换文字内容。
          </template>
        </el-alert>
      </div>

      <div v-else class="progress-section">
        <el-steps :active="progressStep" finish-status="success" align-center>
          <el-step title="版面分析" />
          <el-step title="文本翻译" />
          <el-step title="PDF 渲染" />
          <el-step title="完成" />
        </el-steps>

        <div class="progress-bar-wrapper">
          <el-progress
            :percentage="progress"
            :status="progressStatus"
            :stroke-width="14"
            :text-inside="true"
          />
        </div>

        <p class="progress-message">{{ currentMessage }}</p>

        <div v-if="downloadUrl" class="download-section">
          <el-button type="primary" size="large" @click="handleDownload" class="download-btn">
            <el-icon><Download /></el-icon>
            下载翻译后的 PDF
          </el-button>
          <el-button
            v-if="previewUrl"
            type="success"
            size="large"
            @click="handlePreview"
            class="download-btn"
          >
            <el-icon><View /></el-icon>
            预览翻译 PDF
          </el-button>
        </div>

        <div v-if="expiresAtMsg" class="expiry-notice">
          <el-alert type="warning" :closable="false" show-icon>
            <template #title>
              <span>翻译文件 {{ expiresAtMsg }}，请及时下载</span>
            </template>
          </el-alert>
        </div>

        <div v-if="downloadUrl" class="retranslate-section">
          <el-button size="small" @click="startNewTranslation">
            <el-icon><Refresh /></el-icon>
            重新翻译
          </el-button>
        </div>

        <div v-if="errorMessage" class="error-section">
          <el-alert type="error" :closable="false" show-icon>
            <template #title>{{ errorMessage }}</template>
          </el-alert>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <template v-if="!showProgress">
          <el-button @click="visible = false">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="handleStartTranslate">
            <el-icon><VideoPlay /></el-icon>
            开始翻译
          </el-button>
        </template>
        <template v-else>
          <el-button
            v-if="!downloadUrl && !errorMessage && !isCancelled"
            type="default"
            @click="handleBackground"
          >
            <el-icon><SwitchButton /></el-icon>
            后台运行
          </el-button>
          <el-button
            v-if="!downloadUrl && !errorMessage && !isCancelled"
            type="danger"
            @click="handleCancel"
          >
            <el-icon><Close /></el-icon>
            停止翻译
          </el-button>

          <el-button
            v-if="errorMessage"
            type="danger"
            @click="handleRetry"
          >
            重新开始
          </el-button>
          <el-button @click="handleClose">关闭</el-button>
        </template>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, VideoPlay, SwitchButton, Close, View, Refresh } from '@element-plus/icons-vue'
import {
  startPdfTranslate,
  getPdfTranslateStatus,
  cancelPdfTranslate,
  checkExistingTranslation,
} from '@/api/pdfTranslate'
import { getBeijingAgeDays } from '@/utils/time'

const props = defineProps<{
  modelValue: boolean
  literatureId: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const STORAGE_KEY = 'pdf_translate_task'
const POLL_INTERVAL = 5000

interface StoredTask {
  literatureId: string
  taskId: string
  sourceLang: string
  targetLang: string
  outputMode: string
  startedAt: number
  cancelled?: boolean
}

function getStoredTask(): StoredTask | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    return JSON.parse(raw)
  } catch {
    return null
  }
}

function setStoredTask(task: StoredTask | null) {
  if (task) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(task))
  } else {
    localStorage.removeItem(STORAGE_KEY)
  }
}

const sourceLang = ref('en')
const targetLang = ref('zh')
const outputMode = ref('mono')
const submitting = ref(false)

const taskId = ref('')
const progress = ref(0)
const currentMessage = ref('')
const errorMessage = ref('')
const downloadUrl = ref('')
const previewUrl = ref('')
const runningInBackground = ref(false)
const taskCompletedInBackground = ref(false)
const isCancelled = ref(false)
const reTranslating = ref(false)
const expiresAtMsg = ref('')

function formatExpiryMsg(isoStr: string): string {
  try {
    const ageDays = getBeijingAgeDays(isoStr)
    if (ageDays >= 3) return '已过期'
    const remainingMs = 3 * 24 * 60 * 60 * 1000 - ageDays * 24 * 60 * 60 * 1000
    if (remainingMs <= 0) return '已过期'
    const days = Math.floor(remainingMs / (1000 * 60 * 60 * 24))
    const hours = Math.floor((remainingMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
    if (days > 0) return `还有 ${days} 天 ${hours} 小时后过期`
    return `还有 ${hours} 小时后过期`
  } catch {
    return '3 天后自动删除'
  }
}

let pollTimer: ReturnType<typeof setInterval> | null = null

const dialogTitle = computed(() => {
  if (isCancelled.value) return 'PDF 原位翻译（已取消）'
  if (runningInBackground.value) return 'PDF 原位翻译（后台运行中）'
  if (downloadUrl.value) return 'PDF 原位翻译（已完成）'
  if (showProgress.value && !reTranslating.value) return 'PDF 原位翻译（处理中）'
  return 'PDF 原位翻译'
})

const showProgress = computed(() => !!taskId.value)

const progressStep = computed(() => {
  if (progress.value >= 85) return 4
  if (progress.value >= 60) return 3
  if (progress.value >= 30) return 2
  if (progress.value >= 10) return 1
  return 0
})

const progressStatus = computed(() => {
  if (errorMessage.value) return 'exception'
  if (progress.value >= 100) return 'success'
  return ''
})

async function checkExisting() {
  if (!props.literatureId) return
  try {
    const resp = await checkExistingTranslation(props.literatureId)
    const data = resp.data
    if (data.has_translation && data.download_url) {
      downloadUrl.value = data.download_url
      previewUrl.value = data.preview_url || ''
      progress.value = 100
      currentMessage.value = '翻译文件已就绪'
      taskId.value = 'existing'
      expiresAtMsg.value = formatExpiryMsg(data.expires_at || '')
      runningInBackground.value = false
      taskCompletedInBackground.value = false
      isCancelled.value = false
      reTranslating.value = false
    }
  } catch {
    // 检查失败，使用默认翻译表单
  }
}

function startNewTranslation() {
  reTranslating.value = true
  taskId.value = ''
  progress.value = 0
  currentMessage.value = ''
  errorMessage.value = ''
  downloadUrl.value = ''
  previewUrl.value = ''
  expiresAtMsg.value = ''
  runningInBackground.value = false
  taskCompletedInBackground.value = false
  isCancelled.value = false
  stopPolling()
  setStoredTask(null)
}

async function handleStartTranslate() {
  if (sourceLang.value === targetLang.value) {
    ElMessage.warning('源语言和目标语言不能相同')
    return
  }

  submitting.value = true
  errorMessage.value = ''
  try {
    const resp = await startPdfTranslate(
      props.literatureId,
      sourceLang.value,
      targetLang.value,
      outputMode.value,
    )
    taskId.value = resp.data.task_id
    currentMessage.value = resp.data.message
    progress.value = 0
    runningInBackground.value = false
    taskCompletedInBackground.value = false
    isCancelled.value = false
    reTranslating.value = false

    setStoredTask({
      literatureId: props.literatureId,
      taskId: taskId.value,
      sourceLang: sourceLang.value,
      targetLang: targetLang.value,
      outputMode: outputMode.value,
      startedAt: Date.now(),
    })

    startPolling()
  } catch (err: any) {
    const detail = err.response?.data?.detail || '启动翻译任务失败'
    errorMessage.value = detail
    ElMessage.error(detail)
  } finally {
    submitting.value = false
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(async () => {
    if (!taskId.value) return
    try {
      const resp = await getPdfTranslateStatus(props.literatureId, taskId.value)
      const data = resp.data
      progress.value = data.progress
      currentMessage.value = data.message

      if (data.status === 'completed' && data.download_url) {
        downloadUrl.value = data.download_url
        previewUrl.value = data.preview_url || ''
        progress.value = 100
        currentMessage.value = '翻译完成，请下载文件'
        stopPolling()
        setStoredTask(null)
        if (runningInBackground.value) {
          taskCompletedInBackground.value = true
          ElMessage.success({
            message: 'PDF 原位翻译已完成，可下载文件',
            duration: 5000,
          })
        } else {
          ElMessage.success('PDF 原位翻译完成')
        }
      } else if (data.status === 'cancelled') {
        isCancelled.value = true
        currentMessage.value = data.message || '翻译已被取消'
        stopPolling()
        setStoredTask(null)
        ElMessage.warning('PDF 翻译已取消')
      } else if (data.status === 'failed') {
        errorMessage.value = data.message || '翻译失败'
        stopPolling()
        setStoredTask(null)
        ElMessage.error(errorMessage.value)
      }
    } catch {
      // 轮询失败，继续尝试
    }
  }, POLL_INTERVAL)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function handleBackground() {
  runningInBackground.value = true
  visible.value = false
  ElMessage.info('PDF 翻译任务转入后台运行，处理完成后将通知你')
}

function handleDownload() {
  if (!downloadUrl.value) return
  const token = localStorage.getItem('token')
  const url = '/api/v1' + downloadUrl.value
  const a = document.createElement('a')
  a.href = url
  a.download = ''
  if (token) {
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.blob()
      })
      .then((blob) => {
        const objectUrl = URL.createObjectURL(blob)
        a.href = objectUrl
        a.click()
        URL.revokeObjectURL(objectUrl)
      })
      .catch((err) => {
        console.error('Download failed:', err)
        ElMessage.error('下载失败，请重试')
      })
  } else {
    a.click()
  }
}

function handlePreview() {
  if (!previewUrl.value) return
  const token = localStorage.getItem('token')
  const url = '/api/v1' + previewUrl.value
  if (token) {
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.blob()
      })
      .then((blob) => {
        const objectUrl = URL.createObjectURL(blob)
        window.open(objectUrl, '_blank')
      })
      .catch((err) => {
        console.error('Preview failed:', err)
        ElMessage.error('预览失败，请重试')
      })
  } else {
    window.open(url, '_blank')
  }
}

function handleRetry() {
  taskId.value = ''
  progress.value = 0
  currentMessage.value = ''
  errorMessage.value = ''
  downloadUrl.value = ''
  previewUrl.value = ''
  runningInBackground.value = false
  taskCompletedInBackground.value = false
  isCancelled.value = false
  setStoredTask(null)
  stopPolling()
}

async function handleCancel() {
  if (!taskId.value) return
  try {
    await cancelPdfTranslate(props.literatureId, taskId.value)
  } catch (err: any) {
    if (err.response) {
      const status = err.response.status
      if (status === 400) {
        ElMessage.warning('翻译任务已完成或已取消，无需重复操作')
      } else if (status === 404) {
        ElMessage.warning('翻译任务不存在或已过期')
      } else {
        ElMessage.error(err.response.data?.detail || '取消失败，请稍后重试')
      }
    } else {
      ElMessage.warning('网络连接异常，翻译任务可能仍在后台运行')
    }
  }
  stopPolling()
  isCancelled.value = true
  currentMessage.value = '翻译已被取消'

  const stored = getStoredTask()
  if (stored) {
    stored.cancelled = true
    setStoredTask(stored)
  }
}

function handleClose() {
  if (taskId.value && !downloadUrl.value && !errorMessage.value && !isCancelled.value) {
    runningInBackground.value = true
    ElMessage.info('PDF 翻译任务转入后台运行，可稍后回来下载')
  } else if (isCancelled.value) {
    resetState()
  }
  visible.value = false
}

function handleDialogClose() {
  if (taskId.value && !downloadUrl.value && !errorMessage.value && !isCancelled.value) {
    runningInBackground.value = true
  }
}

function resetState() {
  taskId.value = ''
  progress.value = 0
  currentMessage.value = ''
  errorMessage.value = ''
  downloadUrl.value = ''
  previewUrl.value = ''
  runningInBackground.value = false
  taskCompletedInBackground.value = false
  isCancelled.value = false
  stopPolling()
  setStoredTask(null)
}

async function restoreTask() {
  const stored = getStoredTask()
  if (!stored) return
  if (stored.literatureId !== props.literatureId) {
    setStoredTask(null)
    return
  }

  const age = Date.now() - stored.startedAt
  if (age > 3600000) {
    setStoredTask(null)
    return
  }

  if (stored.cancelled) {
    resetState()
    return
  }

  taskId.value = stored.taskId
  sourceLang.value = stored.sourceLang
  targetLang.value = stored.targetLang
  outputMode.value = stored.outputMode
  runningInBackground.value = true

  try {
    const resp = await getPdfTranslateStatus(props.literatureId, taskId.value)
    const data = resp.data
    progress.value = data.progress
    currentMessage.value = data.message

    if (data.status === 'completed' && data.download_url) {
      downloadUrl.value = data.download_url
      progress.value = 100
      currentMessage.value = '翻译完成，请下载文件'
      setStoredTask(null)
    } else if (data.status === 'cancelled') {
      isCancelled.value = true
      currentMessage.value = data.message || '翻译已被取消'
      setStoredTask(null)
    } else if (data.status === 'failed') {
      errorMessage.value = data.message || '翻译失败'
      setStoredTask(null)
    } else {
      startPolling()
    }
  } catch {
    resetState()
  }
}

watch(visible, async (val) => {
  if (val) {
    stopPolling()
    const stored = getStoredTask()
    if (stored) {
      await restoreTask()
    } else {
      await checkExisting()
    }
  }
})

onMounted(() => {
  const stored = getStoredTask()
  if (!stored || stored.literatureId !== props.literatureId || stored.cancelled) return
  getPdfTranslateStatus(props.literatureId, stored.taskId)
    .then((resp) => {
      const data = resp.data
      if (data.status === 'completed' && data.download_url) {
        taskCompletedInBackground.value = true
        ElMessage.success({
          message: '后台 PDF 翻译已完成，可下载文件',
          duration: 5000,
        })
      }
    })
    .catch(() => {
      setStoredTask(null)
    })
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.pdf-translate-dialog {
  min-height: 200px;
}

.config-section {
  padding: 0 4px;
}

.config-section .el-radio {
  display: flex;
  align-items: flex-start;
  margin-bottom: 12px;
  height: auto;
  padding: 10px 12px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

.mode-label {
  font-weight: 600;
  display: block;
}

.mode-desc {
  font-size: 12px;
  color: var(--text-muted);
  display: block;
  margin-top: 2px;
}

.info-alert {
  margin-top: 16px;
}

.progress-section {
  padding: 0 8px;
}

.progress-bar-wrapper {
  margin: 24px 0 12px;
}

.progress-message {
  text-align: center;
  color: var(--text-secondary);
  font-size: 13px;
  margin: 8px 0 16px;
}

.download-section {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 20px;
}

.download-btn {
  min-width: 160px;
}

.expiry-notice {
  margin-top: 16px;
}

.retranslate-section {
  text-align: center;
  margin-top: 8px;
}

.error-section {
  margin-top: 16px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>