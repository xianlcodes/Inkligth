<template>
  <el-dialog
    v-model="visible"
    title="导出论文"
    width="520px"
    :close-on-click-modal="false"
    @open="onOpen"
  >
    <el-form label-position="top">
      <el-form-item label="导出格式">
        <el-radio-group v-model="format" class="format-group">
          <el-radio-button value="word">
            <el-icon><Document /></el-icon>
            <span>Word (.docx)</span>
          </el-radio-button>
          <el-radio-button value="latex">
            <el-icon><Tickets /></el-icon>
            <span>LaTeX (.tex)</span>
          </el-radio-button>
          <el-radio-button value="pdf">
            <el-icon><Reading /></el-icon>
            <span>PDF</span>
          </el-radio-button>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="导出内容">
        <el-radio-group v-model="sourceType">
          <el-radio value="literature">论文原文</el-radio>
          <el-radio value="translation">论文译文</el-radio>
          <el-radio value="note">论文笔记</el-radio>
        </el-radio-group>
      </el-form-item>

      <!-- LaTeX/PDF 模板选择 -->
      <el-form-item v-if="format !== 'word'" label="LaTeX 模板">
        <el-select v-model="template" style="width: 100%">
          <el-option label="通用 (Generic)" value="generic" />
          <el-option label="IEEE 会议" value="ieee" />
          <el-option label="ACM" value="acm" />
          <el-option label="NeurIPS" value="neurips" />
          <el-option label="LNCS" value="lncs" />
        </el-select>
      </el-form-item>

      <el-form-item label="文件名">
        <el-input v-model="filename" :placeholder="defaultFilename">
          <template #append>.{{ format }}</template>
        </el-input>
      </el-form-item>

      <el-form-item v-if="format === 'word'" label="Word 选项">
        <el-checkbox v-model="wordOptions.include_toc">包含目录</el-checkbox>
        <el-checkbox v-model="wordOptions.page_numbers">显示页码</el-checkbox>
      </el-form-item>
    </el-form>

    <!-- 导出进度 -->
    <div v-if="exporting" class="export-progress">
      <el-progress
        :percentage="exportProgress"
        :status="exportProgressStatus"
        :stroke-width="12"
        :text-inside="true"
      />
      <p class="export-progress-text">{{ exportProgressText }}</p>
    </div>

    <!-- 导出结果 -->
    <div v-if="exportResult" class="export-result">
      <el-alert
        title="导出成功"
        type="success"
        :closable="false"
        show-icon
      />
      <div class="export-result-actions">
        <el-button type="primary" @click="downloadResult">
          <el-icon><Download /></el-icon>
          下载文件
        </el-button>
      </div>
      <p class="export-result-info">
        文件大小: {{ formatSize(exportResult.file_size) }}
      </p>
    </div>

    <template #footer>
      <el-button @click="visible = false" :disabled="exporting">关闭</el-button>
      <el-button
        v-if="!exportResult"
        type="primary"
        :loading="exporting"
        :disabled="!canExport"
        @click="handleExport"
      >
        导出
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Document, Tickets, Reading, Download } from '@element-plus/icons-vue'
import {
  exportWord,
  exportLatex,
  exportPdf,
  getExportDownloadUrl,
  type ExportResponse,
  type WordExportOptions,
  type LatexExportOptions,
} from '@/api/export'

const props = defineProps<{
  literatureId: string
  literatureTitle?: string
}>()

const visible = defineModel<boolean>('visible', { default: false })

const format = ref<'word' | 'latex' | 'pdf'>('word')
const sourceType = ref<'literature' | 'translation' | 'note'>('literature')
const template = ref<string>('generic')
const filename = ref('')
const wordOptions = ref<WordExportOptions>({
  include_toc: true,
  page_numbers: true,
})

const exporting = ref(false)
const exportProgress = ref(0)
const exportProgressStatus = ref<'success' | 'exception' | ''>('')
const exportProgressText = ref('')
const exportResult = ref<ExportResponse | null>(null)

const defaultFilename = computed(() => {
  return props.literatureTitle || 'paper'
})

const canExport = computed(() => {
  return !!props.literatureId
})

function formatSize(bytes: number): string {
  if (bytes <= 0) return '未知'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function onOpen() {
  exportResult.value = null
  exportProgress.value = 0
  exportProgressStatus.value = ''
  exportProgressText.value = ''
  filename.value = defaultFilename.value
}

async function handleExport() {
  if (!props.literatureId) return

  exporting.value = true
  exportProgress.value = 10
  exportProgressText.value = '正在准备导出...'

  try {
    const baseParams = {
      source_type: sourceType.value,
      source_ids: [props.literatureId],
      title: filename.value || defaultFilename.value,
    }

    let result: ExportResponse

    if (format.value === 'word') {
      result = await exportWord({
        ...baseParams,
        options: wordOptions.value,
      })
    } else if (format.value === 'latex') {
      result = await exportLatex({
        ...baseParams,
        options: { template: template.value as LatexExportOptions['template'] },
      })
    } else {
      result = await exportPdf({
        ...baseParams,
        options: { template: template.value as LatexExportOptions['template'] },
      })
    }

    exportResult.value = result
    exportProgress.value = 100
    exportProgressStatus.value = 'success'
    exportProgressText.value = '导出完成!'
    ElMessage.success('导出成功')
  } catch (error: any) {
    exportProgressStatus.value = 'exception'
    exportProgressText.value = error?.response?.data?.detail || '导出失败'
    ElMessage.error(error?.response?.data?.detail || '导出失败')
  } finally {
    exporting.value = false
  }
}

function downloadResult() {
  if (!exportResult.value) return
  const token = localStorage.getItem('token')
  const url = getExportDownloadUrl(exportResult.value.export_id)
  const filename = exportResult.value.filename || `paper.${format.value}`
  if (token) {
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.blob()
      })
      .then((blob) => {
        const objectUrl = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = objectUrl
        a.download = filename
        a.click()
        URL.revokeObjectURL(objectUrl)
        ElMessage.success('开始下载')
      })
      .catch((err) => {
        console.error('Export download failed:', err)
        ElMessage.error('下载失败，请重试')
      })
  } else {
    ElMessage.warning('未检测到登录信息')
  }
}
</script>

<style scoped>
.format-group {
  display: flex;
  gap: 8px;
  width: 100%;
}

.format-group :deep(.el-radio-button) {
  flex: 1;
}

.format-group :deep(.el-radio-button__inner) {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  padding: 12px 8px;
  font-size: 13px;
}

.format-group :deep(.el-radio-button__inner .el-icon) {
  font-size: 18px;
}

.export-progress {
  margin-top: 16px;
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
}

.export-progress-text {
  margin: 8px 0 0;
  font-size: 13px;
  color: var(--text-secondary);
  text-align: center;
}

.export-result {
  margin-top: 16px;
}

.export-result-actions {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}

.export-result-info {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--text-muted);
  text-align: center;
}

:deep(.el-form-item) {
  margin-bottom: 18px;
}

:deep(.el-form-item__label) {
  font-weight: 600;
  font-size: 13px;
  padding-bottom: 4px;
}

.el-checkbox {
  margin-right: 16px;
}
</style>
