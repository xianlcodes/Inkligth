<template>
  <div class="admin-page">
    <div class="section-bar">
      <div class="section-bar-line"></div>
      <h2 class="section-title">系统日志</h2>
      <span class="section-accent">SYSTEM LOGS</span>
    </div>

    <!-- 概览统计：各文件错误/警告计数 -->
    <div class="flex flex-wrap gap-3 mb-4">
      <div
        v-for="f in files"
        :key="f.name"
        class="stats-card"
        :class="{ active: f.name === selectedFile }"
        @click="selectedFile = f.name"
      >
        <div class="flex items-center justify-between gap-3">
          <div>
            <div class="text-sm font-semibold">{{ f.name }}</div>
            <div class="text-xs text-slate-500">{{ formatSize(f.size_bytes) }}</div>
          </div>
          <div class="flex flex-col gap-1 text-xs">
            <el-tag type="danger" size="small">ERROR {{ f.error_count }}</el-tag>
            <el-tag type="warning" size="small">WARN {{ f.warning_count }}</el-tag>
          </div>
        </div>
        <div v-if="f.name !== 'app.log'" class="mt-2 text-right">
          <el-button size="small" text type="danger" @click.stop="removeLogFile(f.name)">删除</el-button>
        </div>
      </div>

      <!-- 日志级别 -->
      <div class="stats-card" style="min-width: 200px">
        <div class="text-sm font-semibold mb-1">日志级别</div>
        <el-select
          v-model="currentLevel"
          size="small"
          style="width: 100%"
          @change="changeLevel"
        >
          <el-option v-for="lv in ['DEBUG', 'INFO', 'WARNING', 'ERROR']" :key="lv" :value="lv" :label="lv" />
        </el-select>
        <div class="text-xs text-slate-400 mt-1">重启后回退到 .env 配置</div>
      </div>
    </div>

    <div class="flex flex-wrap gap-3 mb-4 items-center">
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

      <el-button
        v-if="selectedFile"
        type="warning"
        plain
        @click="clearSelectedLog"
      >
        清空当前文件
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

    <div v-loading="loading" class="log-viewer">
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
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Download } from '@element-plus/icons-vue'
import {
  getSystemLogStats,
  getSystemLogContent,
  getSystemLogBlob,
  setSystemLogLevel,
  clearSystemLog,
  deleteSystemLog,
  type SystemLogFileStats,
} from '@/api/admin'

const files = ref<SystemLogFileStats[]>([])
const selectedFile = ref('')
const currentLevel = ref('INFO')
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

async function loadStats() {
  try {
    const resp = await getSystemLogStats()
    files.value = resp.data.files
    currentLevel.value = resp.data.log_level
    if (!selectedFile.value && files.value.length > 0) {
      selectedFile.value = files.value[0].name
    }
  } catch {
    files.value = []
  }
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

async function refreshAll() {
  await loadStats()
  await loadContent()
}

async function changeLevel(level: string) {
  if (!level) return
  try {
    await ElMessageBox.confirm(
      `确认把日志级别调整为 ${level}？DEBUG 会显著增加日志量，排查完请记得改回 INFO。`,
      '调整日志级别',
      { confirmButtonText: '确认', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    currentLevel.value = files.value.length ? (await getSystemLogStats()).data.log_level : 'INFO'
    return
  }
  try {
    await setSystemLogLevel(level)
    currentLevel.value = level
    ElMessage.success(`日志级别已调整为 ${level}（立即生效，重启后回退）`)
  } catch {
    ElMessage.error('调整失败，请稍后重试')
    await loadStats()
  }
}

async function clearSelectedLog() {
  if (!selectedFile.value) return
  try {
    await ElMessageBox.confirm(
      `确认清空 ${selectedFile.value} 的全部内容？此操作不可恢复。`,
      '清空日志文件',
      { confirmButtonText: '清空', cancelButtonText: '取消', type: 'warning' },
    )
  } catch { return }
  try {
    await clearSystemLog(selectedFile.value)
    ElMessage.success('日志文件已清空')
    await refreshAll()
  } catch {
    ElMessage.error('清空失败，请稍后重试')
  }
}

async function removeLogFile(name: string) {
  try {
    await ElMessageBox.confirm(
      `确认删除历史日志文件 ${name}？此操作不可恢复。`,
      '删除日志文件',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'error' },
    )
  } catch { return }
  try {
    await deleteSystemLog(name)
    ElMessage.success(`已删除 ${name}`)
    if (selectedFile.value === name) selectedFile.value = 'app.log'
    await refreshAll()
  } catch {
    ElMessage.error('删除失败，请稍后重试')
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
    refreshTimer = window.setInterval(async () => {
      await loadStats()
      await loadContent()
    }, 10_000)
  }
})

watch(selectedFile, loadContent)
</script>

<style scoped>
.stats-card {
  background: var(--bg-primary, #fff);
  border: 1px solid var(--border-color, #e2e8f0);
  border-radius: 8px;
  padding: 10px 14px;
  min-width: 180px;
  cursor: pointer;
  transition: border-color 0.15s;
}

.stats-card:hover {
  border-color: var(--el-color-primary, #409eff);
}

.stats-card.active {
  border-color: var(--el-color-primary, #409eff);
  box-shadow: 0 0 0 1px var(--el-color-primary, #409eff) inset;
}

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
