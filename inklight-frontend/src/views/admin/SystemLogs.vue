<template>
  <div class="admin-page">
    <div class="section-bar">
      <div class="section-bar-line"></div>
      <h2 class="section-title">系统日志</h2>
      <span class="section-accent">SYSTEM LOGS</span>
    </div>

    <div class="flex flex-wrap gap-3 mb-4 items-center">
      <el-select v-model="selectedFile" style="width: 200px">
        <el-option v-for="f in files" :key="f.name" :value="f.name"
          :label="`${f.name} (${formatSize(f.size_bytes)})`" />
      </el-select>

      <el-select v-model="filterLevel" style="width: 130px" clearable placeholder="级别" @change="loadContent">
        <el-option label="全部级别" value="" />
        <el-option label="ERROR" value="ERROR" />
        <el-option label="WARNING" value="WARNING" />
        <el-option label="INFO" value="INFO" />
        <el-option label="DEBUG" value="DEBUG" />
      </el-select>

      <el-input
        v-model="filterKeyword"
        placeholder="关键词（request_id / task_id / 报错内容...）"
        clearable
        style="width: 320px"
        @keyup.enter="loadContent"
        @clear="loadContent"
      />

      <el-select v-model="lineCount" style="width: 120px" @change="loadContent">
        <el-option v-for="n in [200, 500, 1000, 2000]" :key="n" :value="n" :label="`最近 ${n} 行`" />
      </el-select>

      <el-button type="primary" :loading="loading" @click="loadContent">
        <el-icon class="mr-1"><Refresh /></el-icon>刷新
      </el-button>

      <el-button :disabled="!selectedFile" @click="downloadLog">
        <el-icon class="mr-1"><Download /></el-icon>下载
      </el-button>

      <div class="ml-auto flex items-center gap-2">
        <span class="text-sm text-slate-500">自动刷新</span>
        <el-switch v-model="autoRefresh" />
      </div>
    </div>

    <div v-if="contentMeta" class="text-xs text-slate-500 mb-2">
      共 {{ contentMeta.total_lines }} 行，显示过滤后最近 {{ contentMeta.returned_lines }} 行
      <el-tag v-if="contentMeta.truncated" type="warning" size="small" class="ml-2">已按上限截断</el-tag>
    </div>

    <div v-loading="loading" class="log-viewer" >
      <pre class="log-pre"><code><span
        v-for="(line, i) in logLines"
        :key="i"
        :class="lineClass(line)"
      >{{ line }}
</span></code></pre>
      <el-empty v-if="!loading && logLines.length === 0" description="暂无日志" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Download } from '@element-plus/icons-vue'
import {
  getSystemLogFiles,
  getSystemLogContent,
  getSystemLogBlob,
  type SystemLogFile,
} from '@/api/admin'

const files = ref<SystemLogFile[]>([])
const selectedFile = ref('')
const filterLevel = ref('')
const filterKeyword = ref('')
const lineCount = ref(500)
const loading = ref(false)
const autoRefresh = ref(false)
const logLines = ref<string[]>([])
const contentMeta = ref<{ total_lines: number; returned_lines: number; truncated: boolean } | null>(null)

let refreshTimer: number | null = null

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function lineClass(line: string): string {
  if (line.includes('| ERROR |') || line.includes('| CRITICAL |')) return 'log-error'
  if (line.includes('| WARNING |')) return 'log-warning'
  if (line.includes('| DEBUG |')) return 'log-debug'
  return 'log-info'
}

async function loadFiles() {
  try {
    const resp = await getSystemLogFiles()
    files.value = resp.data.files
    if (!selectedFile.value && files.value.length > 0) {
      selectedFile.value = files.value[0].name
    }
  } catch { files.value = [] }
}

async function loadContent() {
  if (!selectedFile.value) return
  loading.value = true
  try {
    const resp = await getSystemLogContent({
      name: selectedFile.value,
      lines: lineCount.value,
      level: filterLevel.value || undefined,
      keyword: filterKeyword.value || undefined,
    })
    logLines.value = resp.data.lines
    contentMeta.value = {
      total_lines: resp.data.total_lines,
      returned_lines: resp.data.returned_lines,
      truncated: resp.data.truncated,
    }
  } catch {
    logLines.value = []
    contentMeta.value = null
  } finally {
    loading.value = false
  }
}

async function downloadLog() {
  if (!selectedFile.value) return
  try {
    const resp = await getSystemLogBlob(selectedFile.value)
    const url = URL.createObjectURL(resp.data)
    const a = document.createElement('a')
    a.href = url
    a.download = selectedFile.value
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    ElMessage.error('下载失败，请稍后重试')
  }
}

async function refreshAll() {
  await loadFiles()
  await loadContent()
}

onMounted(async () => {
  await refreshAll()
})

onUnmounted(() => {
  if (refreshTimer !== null) window.clearInterval(refreshTimer)
})

watch(autoRefresh, (on) => {
  if (refreshTimer !== null) {
    window.clearInterval(refreshTimer)
    refreshTimer = null
  }
  if (on) {
    refreshTimer = window.setInterval(loadContent, 10_000)
  }
})

watch(selectedFile, loadContent)
</script>

<style scoped>
.log-viewer {
  background: var(--bg-primary, #fff);
  border: 1px solid var(--border-color, #e2e8f0);
  border-radius: 8px;
  min-height: 420px;
  max-height: 70vh;
  overflow: auto;
}

.log-pre {
  margin: 0;
  padding: 12px 16px;
  font-family: 'JetBrains Mono', Consolas, Menlo, monospace;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}

.log-error { color: #dc2626; }
.log-warning { color: #d97706; }
.log-debug { color: #94a3b8; }
.log-info { color: #334155; }
</style>
