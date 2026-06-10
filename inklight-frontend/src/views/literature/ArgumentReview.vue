<template>
  <div class="argument-review">
    <!-- Header -->
    <div class="review-header">
      <div class="review-header-left">
        <el-button text @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <h2 class="review-title">论文评审</h2>
        <span v-if="literatureTitle" class="review-lit-title">{{ literatureTitle }}</span>
      </div>
      <div class="review-header-actions">
        <el-button
          type="primary"
          :loading="ledgerBuilding"
          :disabled="reviewRunning"
          @click="handleBuildLedger"
        >
          <el-icon><List /></el-icon>
          构建承诺台账
        </el-button>
        <el-button
          type="success"
          :loading="reviewRunning"
          :disabled="ledgerBuilding"
          @click="handleRunReview"
        >
          <el-icon><ChatDotSquare /></el-icon>
          运行评审
        </el-button>
      </div>
    </div>

    <!-- SSE Progress -->
    <div v-if="sseProgress.visible" class="sse-progress-bar" :class="sseProgress.status">
      <el-icon v-if="sseProgress.status === 'running'" class="is-loading"><Loading /></el-icon>
      <el-icon v-else-if="sseProgress.status === 'success'"><CircleCheck /></el-icon>
      <el-icon v-else-if="sseProgress.status === 'error'"><CircleClose /></el-icon>
      <span class="sse-progress-text">{{ sseProgress.message }}</span>
      <el-button v-if="sseProgress.status === 'running'" text size="small" @click="cancelSSE">
        取消
      </el-button>
    </div>

    <!-- Feature descriptions (permanently visible) -->
    <div class="feature-bar">
      <span class="feature-item">
        <el-tag size="small" type="primary" effect="plain">承诺台账</el-tag>
        从摘要/引言提取研究承诺，在方法/实验部分检查兑现情况
      </span>
      <span class="feature-item">
        <el-tag size="small" type="success" effect="plain">多角度评审</el-tag>
        从方法论、实验、写作、魔鬼代言人四个视角并行评审
      </span>
    </div>

    <!-- Content -->
    <div v-loading="loading" class="review-content">

      <template v-if="ledger || reviewSession">
        <el-tabs v-model="activeTab" class="review-tabs">
          <!-- ── Ledger Tab ── -->
          <el-tab-pane label="承诺台账" name="ledger">
            <div v-if="ledger" class="ledger-summary">
              <el-alert
                :title="ledgerSummaryMessage"
                type="info"
                :closable="false"
                show-icon
                class="ledger-summary-alert"
              />
            </div>

            <div v-if="ledger && ledger.promises.length > 0" class="promise-table-wrapper">
              <el-table :data="ledger.promises" style="width:100%" stripe size="small">
                <el-table-column label="序号" type="index" width="50" />
                <el-table-column label="承诺原文" min-width="260">
                  <template #default="{ row }">
                    <div class="promise-cell">
                      <p class="promise-text">{{ row.claim_text }}</p>
                      <span v-if="row.claim_section" class="promise-section">{{ row.claim_section }}</span>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column label="严重程度" width="100" align="center">
                  <template #default="{ row }">
                    <el-tag :type="severityTagType(row.severity)" size="small">
                      {{ severityLabel(row.severity) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="兑现状态" width="100" align="center">
                  <template #default="{ row }">
                    <el-tag :type="statusTagType(row.user_overridden ? (row.user_status || row.status) : row.status)" size="small">
                      {{ statusLabel(row.user_overridden ? (row.user_status || row.status) : row.status) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="兑现证据" min-width="200">
                  <template #default="{ row }">
                    <el-popover
                      v-if="row.discharge_text"
                      placement="right"
                      :width="420"
                      trigger="click"
                      :hide-after="0"
                    >
                      <template #reference>
                        <div class="discharge-trigger">
                          <p class="discharge-text">{{ row.discharge_text.slice(0, 80) }}{{ row.discharge_text.length > 80 ? '...' : '' }}</p>
                          <span v-if="row.discharge_text.length > 80" class="discharge-expand">查看全文</span>
                        </div>
                      </template>
                      <div class="discharge-popover-body">
                        <p class="discharge-popover-text">{{ row.discharge_text }}</p>
                      </div>
                    </el-popover>
                    <span v-else class="no-discharge">无</span>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="120" align="center">
                  <template #default="{ row }">
                    <el-dropdown trigger="click" @command="(cmd: string) => handleOverrideStatus(row, cmd)">
                      <el-button size="small" text>
                        覆盖 <el-icon><ArrowDown /></el-icon>
                      </el-button>
                      <template #dropdown>
                        <el-dropdown-menu>
                          <el-dropdown-item command="paid">已兑现</el-dropdown-item>
                          <el-dropdown-item command="partial">部分兑现</el-dropdown-item>
                          <el-dropdown-item command="unpaid">未兑现</el-dropdown-item>
                          <el-dropdown-item command="mismatch">存在矛盾</el-dropdown-item>
                        </el-dropdown-menu>
                      </template>
                    </el-dropdown>
                  </template>
                </el-table-column>
              </el-table>
            </div>

            <el-empty
              v-if="ledger && ledger.promises.length === 0"
              description="未识别出研究承诺"
            />
          </el-tab-pane>

          <!-- ── Review Tab ── -->
          <el-tab-pane label="评审结果" name="review">
            <div v-if="reviewSession">
              <!-- Overall Assessment -->
              <div v-if="reviewSession.overall_assessment" class="assessment-card">
                <div class="assessment-header">
                  <el-icon><ChatDotSquare /></el-icon>
                  <span>总体评价: {{ reviewSession.overall_assessment }}</span>
                </div>
                <p v-if="reviewSession.strengths" class="assessment-text">
                  <strong>优势:</strong> {{ reviewSession.strengths }}
                </p>
                <p v-if="reviewSession.top_issues" class="assessment-text">
                  <strong>主要问题:</strong> {{ reviewSession.top_issues }}
                </p>
              </div>

              <!-- Review Points -->
              <div class="review-points-header">
                <span class="review-points-title">评审要点 ({{ filteredPoints.length }})</span>
                <div class="review-points-filters">
                  <el-select
                    v-model="reviewFilter.category"
                    placeholder="角度过滤"
                    size="small"
                    clearable
                    style="width:140px"
                  >
                    <el-option label="全部角度" value="" />
                    <el-option label="方法论" value="methodology" />
                    <el-option label="实验" value="experiment" />
                    <el-option label="写作" value="writing" />
                    <el-option label="质疑" value="devils_advocate" />
                  </el-select>
                  <el-select
                    v-model="reviewFilter.severity"
                    placeholder="严重程度"
                    size="small"
                    clearable
                    style="width:120px"
                  >
                    <el-option label="全部" value="" />
                    <el-option label="严重" value="critical" />
                    <el-option label="主要" value="major" />
                    <el-option label="次要" value="minor" />
                    <el-option label="建议" value="suggestion" />
                  </el-select>
                </div>
              </div>

              <div class="review-points-list">
                <div
                  v-for="point in filteredPoints"
                  :key="point.id"
                  class="review-point-card"
                >
                  <div class="point-header">
                    <div class="point-tags">
                      <el-tag :type="severityTagType(point.severity)" size="small">
                        {{ severityLabel(point.severity) }}
                      </el-tag>
                      <el-tag size="small" effect="plain">{{ point.category }}</el-tag>
                      <el-tag
                        v-if="point.rebuttal_status"
                        :type="rebuttalStatusTag(point.rebuttal_status)"
                        size="small"
                      >
                        {{ rebuttalStatusLabel(point.rebuttal_status) }}
                      </el-tag>
                    </div>
                    <div class="point-actions">
                      <el-button
                        v-if="!point.rebuttal"
                        text
                        size="small"
                        type="primary"
                        @click="openRebuttal(point)"
                      >
                        答辩
                      </el-button>
                      <el-button
                        v-else-if="point.rebuttal_status !== 'accepted'"
                        text
                        size="small"
                        type="primary"
                        @click="openRebuttal(point)"
                      >
                        补充答辩
                      </el-button>
                    </div>
                  </div>
                  <h4 class="point-title">{{ point.title }}</h4>
                  <p class="point-desc">{{ point.description }}</p>
                  <p v-if="point.suggestion" class="point-suggestion">
                    <strong>建议:</strong> {{ point.suggestion }}
                  </p>

                  <!-- Rebuttal display -->
                  <div v-if="point.rebuttal" class="rebuttal-display">
                    <div class="rebuttal-item author-rebuttal">
                      <span class="rebuttal-label">作者答辩:</span>
                      <p class="rebuttal-text">{{ point.rebuttal }}</p>
                    </div>
                    <div v-if="point.reviewer_response" class="rebuttal-item reviewer-response">
                      <span class="rebuttal-label">审稿人回复:</span>
                      <p class="rebuttal-text">{{ point.reviewer_response }}</p>
                      <el-tag
                        :type="rebuttalStatusTag(point.rebuttal_status)"
                        size="small"
                      >
                        {{ rebuttalStatusLabel(point.rebuttal_status) }}
                      </el-tag>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <el-empty
              v-if="!reviewSession"
              description="请点击上方「运行评审」按钮"
            />
          </el-tab-pane>
        </el-tabs>
      </template>
    </div>

    <!-- ── Rebuttal Dialog ── -->
    <el-dialog
      v-model="rebuttalDialogVisible"
      title="作者答辩"
      width="560px"
    >
      <div class="rebuttal-dialog-body">
        <div class="rebuttal-point-info">
          <el-tag :type="severityTagType(rebuttalPoint?.severity)" size="small">
            {{ severityLabel(rebuttalPoint?.severity) }}
          </el-tag>
          <span class="rebuttal-point-title">{{ rebuttalPoint?.title }}</span>
        </div>
        <p class="rebuttal-point-desc">{{ rebuttalPoint?.description }}</p>
        <div v-if="rebuttalPoint?.rebuttal" class="rebuttal-history">
          <p class="rebuttal-history-label">你的上一次答辩:</p>
          <p class="rebuttal-history-text">{{ rebuttalPoint?.rebuttal }}</p>
        </div>
        <el-input
          v-model="rebuttalMessage"
          type="textarea"
          :rows="5"
          placeholder="请输入你对评审意见的回复..."
        />
      </div>
      <template #footer>
        <el-button @click="rebuttalDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="rebuttalSaving" @click="handleSubmitRebuttal">
          提交答辩
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft,
  List,
  ChatDotSquare,
  Loading,
  CircleCheck,
  CircleClose,
  ArrowDown,
} from '@element-plus/icons-vue'
import {
  buildLedgerSSE,
  getLedgerByLiterature,
  updatePromise,
  runReviewSSE,
  getReviewByLiterature,
  submitRebuttal,
  type LedgerResponse,
  type ReviewSessionResponse,
  type ReviewPointResponse,
  type PromiseResponse,
} from '@/api/argument'
import { getLiterature, type Literature } from '@/api/literature'

const route = useRoute()
const router = useRouter()

const literatureId = computed(() => route.params.id as string)
const literatureTitle = ref('')
const loading = ref(false)

// SSE state
const sseProgress = ref<{
  visible: boolean
  status: 'running' | 'success' | 'error'
  message: string
}>({
  visible: false,
  status: 'running',
  message: '',
})
let sseAbort: AbortController | null = null

// Ledger
const ledger = ref<LedgerResponse | null>(null)
const ledgerBuilding = ref(false)

// Review
const reviewSession = ref<ReviewSessionResponse | null>(null)
const reviewRunning = ref(false)
const reviewFilter = ref<{ category: string; severity: string }>({
  category: '',
  severity: '',
})

// Rebuttal
const rebuttalDialogVisible = ref(false)
const rebuttalPoint = ref<ReviewPointResponse | null>(null)
const rebuttalMessage = ref('')
const rebuttalSaving = ref(false)

// Tab
const activeTab = ref<string>('ledger')

const filteredPoints = computed(() => {
  if (!reviewSession.value) return []
  let points = reviewSession.value.points
  if (reviewFilter.value.category) {
    points = points.filter(p => p.category === reviewFilter.value.category)
  }
  if (reviewFilter.value.severity) {
    points = points.filter(p => p.severity === reviewFilter.value.severity)
  }
  return points
})

const ledgerSummaryMessage = computed(() => {
  if (!ledger.value) return ''
  const promises = ledger.value.promises
  const total = promises.length
  const paid = promises.filter(p => (p.user_overridden ? p.user_status : p.status) === 'paid').length
  const partial = promises.filter(p => (p.user_overridden ? p.user_status : p.status) === 'partial').length
  const unpaid = promises.filter(p => (p.user_overridden ? p.user_status : p.status) === 'unpaid').length
  return `共识别 ${total} 条研究承诺 — 已兑现: ${paid}, 部分兑现: ${partial}, 未兑现: ${unpaid}`
})

onMounted(async () => {
  loading.value = true
  try {
    const litResp = await getLiterature(literatureId.value)
    literatureTitle.value = litResp.data?.title || ''
  } catch {
    // ok
  }
  await Promise.all([loadLedger(), loadReview()])
  loading.value = false
})

onUnmounted(() => {
  if (sseAbort) sseAbort.abort()
})

async function loadLedger() {
  try {
    const data = await getLedgerByLiterature(literatureId.value)
    ledger.value = data
  } catch {
    ledger.value = null
  }
}

async function loadReview() {
  try {
    const data = await getReviewByLiterature(literatureId.value)
    reviewSession.value = data
  } catch {
    reviewSession.value = null
  }
}

function handleBuildLedger() {
  if (ledgerBuilding.value) return
  ledgerBuilding.value = true
  sseProgress.value = { visible: true, status: 'running', message: '正在构建承诺台账...' }
  ledger.value = null

  sseAbort = buildLedgerSSE(literatureId.value, {
    onProgress: (data) => {
      const msg = (data as Record<string, unknown>).message as string || ''
      sseProgress.value.message = msg
    },
    onPromiseExtracted: () => {
      sseProgress.value.message = '正在提取研究承诺...'
    },
    onPromiseChecked: () => {
      sseProgress.value.message = '正在检查承诺兑现...'
    },
    onAnchored: () => {
      sseProgress.value.message = '正在定位引文...'
    },
    onComplete: async () => {
      sseProgress.value = { visible: true, status: 'success', message: '台账构建完成' }
      ledgerBuilding.value = false
      await loadLedger()
      setTimeout(() => {
        sseProgress.value.visible = false
      }, 2000)
    },
    onError: (errMsg) => {
      sseProgress.value = { visible: true, status: 'error', message: errMsg || '构建失败' }
      ledgerBuilding.value = false
    },
  })
}

function handleRunReview() {
  if (reviewRunning.value) return
  reviewRunning.value = true
  sseProgress.value = { visible: true, status: 'running', message: '正在运行多角度评审...' }
  reviewSession.value = null

  sseAbort = runReviewSSE(literatureId.value, {
    onProgress: (data) => {
      const msg = (data as Record<string, unknown>).message as string || ''
      sseProgress.value.message = msg
    },
    onReviewPoint: () => {
      sseProgress.value.message = '正在生成评审要点...'
    },
    onSynthesizing: () => {
      sseProgress.value.message = '正在综合评审意见...'
    },
    onAssessment: () => {
      sseProgress.value.message = '正在生成总体评价...'
    },
    onComplete: async () => {
      sseProgress.value = { visible: true, status: 'success', message: '评审完成' }
      reviewRunning.value = false
      await loadReview()
      activeTab.value = 'review'
      setTimeout(() => {
        sseProgress.value.visible = false
      }, 2000)
    },
    onError: (errMsg) => {
      sseProgress.value = { visible: true, status: 'error', message: errMsg || '评审失败' }
      reviewRunning.value = false
    },
  })
}

function cancelSSE() {
  if (sseAbort) {
    sseAbort.abort()
    sseAbort = null
  }
  ledgerBuilding.value = false
  reviewRunning.value = false
  sseProgress.value.visible = false
}

async function handleOverrideStatus(promise: PromiseResponse, status: string) {
  if (!promise.id || promise.user_overridden && promise.user_status === status) return
  try {
    await updatePromise(promise.id, status as 'paid' | 'partial' | 'unpaid' | 'mismatch')
    promise.user_overridden = true
    promise.user_status = status
    ElMessage.success('状态已更新')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '更新失败')
  }
}

function openRebuttal(point: ReviewPointResponse) {
  rebuttalPoint.value = point
  rebuttalMessage.value = ''
  rebuttalDialogVisible.value = true
}

async function handleSubmitRebuttal() {
  if (!rebuttalMessage.value.trim() || !rebuttalPoint.value) {
    ElMessage.warning('请输入答辩内容')
    return
  }
  if (!reviewSession.value) return

  rebuttalSaving.value = true
  try {
    await submitRebuttal(reviewSession.value.id, rebuttalPoint.value.id, rebuttalMessage.value.trim())
    ElMessage.success('答辩已提交')
    rebuttalDialogVisible.value = false
    await loadReview()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '提交失败')
  } finally {
    rebuttalSaving.value = false
  }
}

function goBack() {
  if (window.history.state?.back) {
    router.back()
  } else {
    router.push(`/read/${literatureId.value}`)
  }
}

// ── Helpers ──
function severityTagType(s: string): 'danger' | 'warning' | 'info' | 'primary' {
  const map: Record<string, 'danger' | 'warning' | 'info' | 'primary'> = {
    critical: 'danger',
    major: 'warning',
    minor: 'info',
    suggestion: 'primary',
  }
  return map[s] || 'info'
}

function severityLabel(s: string): string {
  const map: Record<string, string> = {
    critical: '严重',
    major: '主要',
    minor: '次要',
    suggestion: '建议',
    error: '核心',
    warning: '重要',
    info: '一般',
  }
  return map[s] || s
}

function statusTagType(s: string): 'success' | 'warning' | 'danger' | 'info' {
  const map: Record<string, 'success' | 'warning' | 'danger' | 'info'> = {
    paid: 'success',
    partial: 'warning',
    unpaid: 'danger',
    mismatch: 'danger',
  }
  return map[s] || 'info'
}

function statusLabel(s: string): string {
  const map: Record<string, string> = {
    paid: '已兑现',
    partial: '部分兑现',
    unpaid: '未兑现',
    mismatch: '存在矛盾',
  }
  return map[s] || s
}

function rebuttalStatusTag(s: string): 'success' | 'warning' | 'danger' | 'info' {
  const map: Record<string, 'success' | 'warning' | 'danger' | 'info'> = {
    accepted: 'success',
    disputed: 'warning',
    rejected: 'danger',
    pending: 'info',
  }
  return map[s] || 'info'
}

function rebuttalStatusLabel(s: string): string {
  const map: Record<string, string> = {
    accepted: '已接受',
    disputed: '有争议',
    rejected: '已拒绝',
    pending: '待审核',
  }
  return map[s] || s
}
</script>

<style scoped>
.argument-review {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-secondary);
}

/* ── Header ── */
.review-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  background: var(--bg-primary);
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
  box-shadow: var(--shadow-xs);
}

.review-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.review-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}

.review-lit-title {
  font-size: 13px;
  color: var(--text-tertiary);
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 2px 8px;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
}

.review-header-actions {
  display: flex;
  gap: 8px;
}

/* ── SSE Progress ── */
.sse-progress-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 24px;
  font-size: 13px;
  flex-shrink: 0;
  border-bottom: 1px solid var(--border-color);
  animation: slideInDown 0.2s ease;
}

.sse-progress-bar.running {
  background: var(--sky-50);
  color: var(--accent-primary);
}

.sse-progress-bar.success {
  background: var(--emerald-50);
  color: var(--emerald-600);
}

.sse-progress-bar.error {
  background: var(--rose-50);
  color: var(--rose-600);
}

.sse-progress-text {
  flex: 1;
}

/* ── Content ── */
.review-content {
  flex: 1;
  overflow: auto;
  padding: 16px 24px;
}

/* ── Feature Bar ── */
.feature-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 20px;
  padding: 8px 24px;
  background: var(--bg-primary);
  border-bottom: 1px solid var(--border-color);
  font-size: 12px;
  color: var(--text-tertiary);
  flex-shrink: 0;
}
.feature-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  line-height: 1.5;
}

/* ── Review Tabs ── */
.review-tabs {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  padding: 8px;
  box-shadow: var(--shadow-xs);
}

/* ── Ledger ── */
.ledger-summary {
  margin-bottom: 16px;
}

.promise-table-wrapper {
  overflow-x: auto;
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
}

.promise-cell {
  max-width: 300px;
}

.promise-text {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
  color: var(--text-primary);
}

.promise-section {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
  display: inline-block;
  padding: 1px 6px;
  background: var(--slate-50);
  border-radius: var(--radius-xs);
}

.discharge-text {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-secondary);
  display: inline;
}

.discharge-trigger {
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 0;
}

.discharge-expand {
  font-size: 11px;
  color: var(--accent-primary);
  white-space: nowrap;
  flex-shrink: 0;
  opacity: 0.7;
  transition: opacity var(--transition-fast);
  font-weight: 500;
}

.discharge-trigger:hover .discharge-expand {
  opacity: 1;
  text-decoration: underline;
}

.discharge-popover-body {
  max-height: 320px;
  overflow-y: auto;
  padding: 4px 0;
}

.discharge-popover-text {
  margin: 0;
  font-size: 13px;
  line-height: 1.7;
  color: var(--text-primary);
  white-space: pre-wrap;
  word-break: break-word;
}

.no-discharge {
  font-size: 12px;
  color: var(--text-muted);
  font-style: italic;
}

/* ── Review Points ── */
.assessment-card {
  padding: 16px 20px;
  background: var(--sky-50);
  border: 1px solid var(--sky-100);
  border-radius: var(--radius-lg);
  margin-bottom: 20px;
  border-left: 4px solid var(--accent-primary);
}

.assessment-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: var(--sky-700);
  margin-bottom: 8px;
}

.assessment-text {
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-primary);
  margin: 6px 0;
}

.review-points-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.review-points-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.review-points-filters {
  display: flex;
  gap: 8px;
}

.review-points-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.review-point-card {
  padding: 16px 20px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  background: var(--bg-primary);
  transition: all var(--transition-base);
  box-shadow: var(--shadow-xs);
}

.review-point-card:hover {
  border-color: var(--sky-200);
  box-shadow: var(--shadow-sm);
}

.point-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}

.point-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.point-actions {
  flex-shrink: 0;
}

.point-title {
  margin: 0 0 6px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: var(--leading-tight);
}

.point-desc {
  margin: 0 0 6px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-secondary);
}

.point-suggestion {
  margin: 0;
  font-size: 13px;
  color: var(--accent-primary);
  line-height: 1.5;
  padding: 8px 12px;
  background: var(--sky-50);
  border-radius: var(--radius-sm);
}

/* ── Rebuttal Display ── */
.rebuttal-display {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rebuttal-item {
  padding: 10px 14px;
  border-radius: var(--radius-md);
}

.author-rebuttal {
  background: var(--amber-50);
  border-left: 3px solid var(--amber-500);
}

.reviewer-response {
  background: var(--emerald-50);
  border-left: 3px solid var(--emerald-500);
}

.rebuttal-label {
  font-size: 12px;
  font-weight: 700;
  display: block;
  margin-bottom: 4px;
  letter-spacing: 0.03em;
}

.author-rebuttal .rebuttal-label {
  color: var(--amber-600);
}

.reviewer-response .rebuttal-label {
  color: var(--emerald-600);
}

.rebuttal-text {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-primary);
}

/* ── Rebuttal Dialog ── */
.rebuttal-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.rebuttal-point-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.rebuttal-point-title {
  font-weight: 600;
  font-size: 14px;
  color: var(--text-primary);
}

.rebuttal-point-desc {
  margin: 0;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.rebuttal-history {
  padding: 10px 14px;
  background: var(--amber-50);
  border-radius: var(--radius-md);
  border-left: 3px solid var(--amber-500);
}

.rebuttal-history-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  margin: 0 0 4px;
}

.rebuttal-history-text {
  margin: 0;
  font-size: 13px;
  color: var(--text-primary);
  line-height: 1.5;
}

/* ── Dark mode adjustments ── */
@media (prefers-color-scheme: dark) {
  .review-point-card {
    border-color: var(--border-muted);
  }
}
</style>
