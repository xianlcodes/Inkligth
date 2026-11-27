<template>
  <div class="admin-page">
    <div class="section-bar">
      <div class="section-bar-line"></div>
      <h2 class="section-title">系统日志</h2>
      <span class="section-accent">SYSTEM LOGS</span>
    </div>

    <!-- ① 今天的状态：一眼看出系统有没有问题 -->
    <el-alert
      :type="bannerType"
      :closable="false"
      show-icon
      class="mb-4"
    >
      <template #title>
        <span class="font-semibold">{{ bannerText }}</span>
      </template>
      <span v-if="todayErrors > 0" class="text-sm">
        点击下方「只看：错误」可以快速筛出这些报错；用户反馈问题时，让 TA 提供报错旁边的 request_id。
      </span>
    </el-alert>

    <!-- ② 看哪一天的日志 -->
    <div class="flex flex-wrap items-center gap-3 mb-3">
      <span class="text-sm text-slate-500">查看：</span>
      <el-radio-group v-model="selectedFile">
        <el-radio-button value="app.log">今天（实时）</el-radio-button>
        <el-radio-button v-for="f in olderFiles" :key="f.name" :value="f.name">
          {{ fileLabel(f) }}
        </el-radio-button>
      </el-radio-group>

      <div class="ml-auto flex items-center gap-2">
        <el-switch v-model="debugMode" active-text="排查模式" />
        <el-tooltip
          content="排查模式：记录每个请求的详细过程，方便定位问题；平时请保持关闭，避免日志过多。重启服务后会自动回到正常模式。"
          placement="top"
        >
          <el-icon class="text-slate-400 cursor-help"><CircleHelp /></el-icon>
        </el-tooltip>
      </div>
    </div>

    <!-- ③ 筛选和操作 -->
    <div class="flex flex-wrap items-center gap-3 mb-3">
      <span class="text-sm text-slate-500">只看：</span>
      <el-radio-group v-model="filterLevel" @change="loadContent">
        <el-radio-button value="">全部</el-radio-button>
        <el-radio-button value="ERROR">错误</el-radio-button>
        <el-radio-button value="WARNING">警告</el-radio-button>
      </el-radio-group>

      <el-input
        v-model="filterKeyword"
        placeholder="按内容搜索（如 request_id、报错文字）"
        clearable
        style="width: 300px"
        @keyup.enter="loadContent"
        @clear="loadContent"
      />

      <el-button type="primary" :loading="loading" @click="loadContent">刷新</el-button>
      <el-button @click="downloadLog">下载这份日志</el-button>
      <el-button v-if="selectedFile === 'app.log'" type="warning" plain @click="clearToday">
        清空今天的日志
      </el-button>
      <el-button v-else type="danger" plain @click="removeOlder">删除这份历史日志</el-button>

      <el-switch v-model="autoRefresh" active-text="自动刷新（10秒）" class="ml-auto" />
    </div>

    <!-- ④ 日志内容 -->
    <div v-loading="loading" class="log-viewer">
      <pre class="log-pre"><code><span
        v-for="(line, i) in logLines"
        :key="i"
        :class="lineClass(line)"
      >{{ line }}
</span></code></pre>
      <el-empty
        v-if="!loading && logLines.length === 0"
        :description="emptyText"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CircleHelp } from 'lucide-vue-next'
import {
  getSystemLogStats,
  getSystemLogContent,
  getSystemLogBlob,
  setSystemLogLevel,
  clearSystemLog,
  deleteSystemLog,
  type SystemLogFileStats,
} from '@/api/admin'

/** 显示给用户的行数上限（后端单次最多 2000 行） */
const LINES = 800

const files = ref<SystemLogFileStats[]>([])
const selectedFile = ref('app.log')
const debugMode = ref(false)
const filterLevel = ref('')
const filterKeyword = ref('')
const loading = ref(false)
const autoRefresh = ref(false)
const logLines = ref<string[]>([])
const contentMeta = ref<{ total_lines: number; returned_lines: number; truncated: boolean } | null>(null)

let refreshTimer: number | null = null
let debugModeInternal = false // 防止 watch 回环

const olderFiles = computed(() =>
  files.value
    .filter((f) => f.name !== 'app.log')
    .sort((a, b) => b.name.localeCompare(a.name)),
)

const todayStats = computed(() => files.value.find((f) => f.name === 'app.log'))

const todayErrors = computed(() => todayStats.value?.error_count ?? 0)
const todayWarnings = computed(() => todayStats.value?.warning_count ?? 0)

const bannerType = computed<'success' | 'warning' | 'error'>(() => {
  if (todayErrors.value > 0) return 'error'
  if (todayWarnings.value > 0) return 'warning'
  return 'success'
})

const bannerText = computed(() => {
  if (!todayStats.value) return '正在加载今天的状态…'
  if (todayErrors.value > 0) {
    return `今天有 ${todayErrors.value} 个错误、${todayWarnings.value} 条警告`
  }
  if (todayWarnings.value > 0) {
    return `今天没有错误，但有 ${todayWarnings.value} 条警告（警告一般不影响使用）`
  }
  return '今天一切正常，没有错误'
})

const emptyText = computed(() =>
  filterLevel.value || filterKeyword.value
    ? '没有符合筛选条件的日志，试试清空筛选条件'
    : selectedFile.value === 'app.log'
      ? '今天还没有日志'
      : '这份历史日志是空的',
)

/** app.log.2026-11-19 → 「11月19日 · 1个错误」 */
function fileLabel(f: SystemLogFileStats): string {
  const m = f.name.match(/^app\.log\.(\d{4})-(\d{2})-(\d{2})$/)
  if (!m) return f.name
  const date = `${parseInt(m[2], 10)}月${parseInt(m[3], 10)}日`
  return f.error_count > 0 ? `${date} · ${f.error_count}个错误` : date
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
    // 排查模式开关与后端实际级别对齐（避免和别的管理员操作打架）
    const backendDebug = resp.data.log_level === 'DEBUG'
    if (backendDebug !== debugModeInternal) {
      debugModeInternal = backendDebug
      debugMode.value = backendDebug
    }
    if (!files.value.some((f) => f.name === selectedFile.value)) {
      selectedFile.value = 'app.log'
    }
  } catch {
    files.value = []
  }
}

async function loadContent() {
  loading.value = true
  try {
    const resp = await getSystemLogContent({
      name: selectedFile.value,
      lines: LINES,
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

/** 排查模式开关 = 全局日志级别 INFO ↔ DEBUG */
watch(debugMode, async (on) => {
  if (on === debugModeInternal) return
  const target = on ? 'DEBUG' : 'INFO'
  try {
    await setSystemLogLevel(target)
    debugModeInternal = on
    ElMessage.success(
      on
        ? '已开启排查模式：日志会详细记录每个请求，排查完请记得关闭'
        : '已回到正常模式',
    )
  } catch {
    debugModeInternal = !on
    debugMode.value = !on
    ElMessage.error('切换失败，请稍后重试')
  }
})

async function clearToday() {
  try {
    await ElMessageBox.confirm(
      '将删除今天日志的全部内容，只保留一条「谁清空的」记录。清空前建议先点「下载这份日志」留个备份。确定继续吗？',
      '清空今天的日志',
      { confirmButtonText: '清空', cancelButtonText: '先不清', type: 'warning' },
    )
  } catch { return }
  try {
    await clearSystemLog('app.log')
    ElMessage.success('已清空')
    await refreshAll()
  } catch {
    ElMessage.error('清空失败，请稍后重试')
  }
}

async function removeOlder() {
  const name = selectedFile.value
  try {
    await ElMessageBox.confirm(
      `将永久删除这份历史日志（${fileLabelByName(name)}）。删除后无法恢复，确定继续吗？`,
      '删除历史日志',
      { confirmButtonText: '删除', cancelButtonText: '先不删', type: 'error' },
    )
  } catch { return }
  try {
    await deleteSystemLog(name)
    ElMessage.success('已删除')
    selectedFile.value = 'app.log'
    await refreshAll()
  } catch {
    ElMessage.error('删除失败，请稍后重试')
  }
}

function fileLabelByName(name: string): string {
  const f = files.value.find((x) => x.name === name)
  return f ? fileLabel(f) : name
}

async function downloadLog() {
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

onMounted(refreshAll)

onUnmounted(() => {
  if (refreshTimer !== null) window.clearInterval(refreshTimer)
})

watch(autoRefresh, (on) => {
  if (refreshTimer !== null) {
    window.clearInterval(refreshTimer)
    refreshTimer = null
  }
  if (on) {
    refreshTimer = window.setInterval(refreshAll, 10_000)
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
  max-height: 65vh;
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
