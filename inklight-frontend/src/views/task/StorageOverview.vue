<template>
  <div class="storage-overview">
    <h2 class="page-title">个人空间</h2>

    <el-row :gutter="20">
      <el-col :span="16">
        <el-card class="storage-card" shadow="never">
          <template #header>
            <span class="card-title">存储空间概览</span>
          </template>
          <div class="storage-summary">
            <div class="storage-numbers">
              <div class="storage-item">
                <span class="storage-label">总空间</span>
                <span class="storage-value">{{ formatBytes(storage?.total_space) }}</span>
              </div>
              <div class="storage-item">
                <span class="storage-label">已用空间</span>
                <span class="storage-value used">{{ formatBytes(storage?.used_space) }}</span>
              </div>
              <div class="storage-item">
                <span class="storage-label">剩余空间</span>
                <span class="storage-value remaining">{{ formatBytes(storage?.remaining_space) }}</span>
              </div>
            </div>
            <el-progress
              :percentage="usagePercent"
              :stroke-width="16"
              :color="progressColor"
              class="storage-progress"
            />
          </div>

          <div class="space-details">
            <div class="detail-title">空间来源明细</div>
            <div class="detail-item">
              <span class="detail-label">基础空间</span>
              <span class="detail-value">{{ formatBytes(storage?.base_space) }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">签到奖励</span>
              <span class="detail-value">{{ formatBytes(storage?.check_in_bonus) }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">邀请奖励</span>
              <span class="detail-value">{{ formatBytes(storage?.invitation_bonus) }}</span>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card class="invite-card" shadow="never">
          <template #header>
            <span class="card-title">我的邀请</span>
          </template>
          <div class="invite-section">
            <div v-if="invitations?.codes.length" class="invite-code-area">
              <div class="invite-code-label">邀请码</div>
              <div class="invite-code-row">
                <code class="invite-code">{{ invitations.codes[0].code }}</code>
                <el-button size="small" type="primary" @click="copyCode">
                  <el-icon><CopyDocument /></el-icon>
                  复制
                </el-button>
              </div>
            </div>
            <div v-else class="no-invite">
              <p>暂无邀请码</p>
            </div>
            <el-button
              size="small"
              type="primary"
              :disabled="(invitations?.codes.length || 0) >= 5"
              :loading="generating"
              class="generate-btn"
              @click="handleGenerate"
            >
              生成邀请码
            </el-button>
          </div>

          <div v-if="invitations?.invited_users.length" class="invited-users">
            <div class="invited-title">已邀请用户</div>
            <div
              v-for="user in invitations.invited_users"
              :key="user.email"
              class="invited-user-item"
            >
              <div class="invited-email">{{ user.email }}</div>
              <div class="invited-meta">
                <span>{{ formatDate(user.registered_at) }}</span>
                <el-tag :type="user.reward_granted ? 'success' : 'warning'" size="small">
                  {{ user.reward_granted ? '已发放' : '待发放' }}
                </el-tag>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="recent-card" shadow="never">
      <template #header>
        <span class="card-title">最近上传文献</span>
      </template>
      <el-table :data="recentLiteratures" style="width: 100%" v-loading="loadingRecent">
        <el-table-column prop="title" label="文献标题" min-width="200" />
        <el-table-column label="大小" width="120">
          <template #default="{ row }">
            {{ formatBytes(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="上传时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loadingRecent && recentLiteratures.length === 0" description="暂无上传文献" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { CopyDocument } from '@element-plus/icons-vue'
import { getStorage, type StorageInfo } from '@/api/storage'
import { getInvitations, generateInvitationCode, type InvitationList } from '@/api/invitation'
import { getLiteratures } from '@/api/literature'

const storage = ref<StorageInfo | null>(null)
const invitations = ref<InvitationList | null>(null)
const recentLiteratures = ref<any[]>([])
const loadingRecent = ref(false)
const generating = ref(false)

const usagePercent = computed(() => {
  if (!storage.value || storage.value.total_space === 0) return 0
  return Math.round((storage.value.used_space / storage.value.total_space) * 100)
})

const progressColor = computed(() => {
  if (usagePercent.value > 90) return '#f56c6c'
  if (usagePercent.value > 70) return '#e6a23c'
  return '#67c23a'
})

function formatBytes(bytes: number | undefined): string {
  if (bytes === undefined || bytes === null || bytes === 0) return '0.00 MB'
  if (bytes >= 1024 * 1024 * 1024) {
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB'
  }
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}

function formatDate(dateStr: string | undefined): string {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

async function copyCode() {
  if (!invitations.value?.codes.length) return
  await navigator.clipboard.writeText(invitations.value.codes[0].code)
  ElMessage.success('邀请码已复制')
}

async function handleGenerate() {
  generating.value = true
  try {
    await generateInvitationCode()
    ElMessage.success('邀请码生成成功')
    await fetchInvitations()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '生成失败')
  } finally {
    generating.value = false
  }
}

async function fetchStorage() {
  try {
    storage.value = await getStorage()
  } catch {
    // ignore
  }
}

async function fetchInvitations() {
  try {
    invitations.value = await getInvitations()
  } catch {
    // ignore
  }
}

async function fetchRecentLiteratures() {
  loadingRecent.value = true
  try {
    const result = await getLiteratures({ limit: 10, skip: 0 })
    recentLiteratures.value = result.data.items || []
  } catch {
    // ignore
  } finally {
    loadingRecent.value = false
  }
}

onMounted(() => {
  fetchStorage()
  fetchInvitations()
  fetchRecentLiteratures()
})
</script>

<style scoped>
.storage-overview {
  max-width: 1100px;
  margin: 0 auto;
}

.page-title {
  font-size: 22px;
  font-weight: 600;
  margin: 0 0 20px;
  color: var(--text-primary);
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.storage-card {
  margin-bottom: 20px;
}

.storage-summary {
  margin-bottom: 20px;
}

.storage-numbers {
  display: flex;
  gap: 40px;
  margin-bottom: 16px;
}

.storage-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.storage-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.storage-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
}

.storage-value.used {
  color: #e6a23c;
}

.storage-value.remaining {
  color: #67c23a;
}

.storage-progress {
  margin-bottom: 8px;
}

.space-details {
  border-top: 1px solid var(--border-light);
  padding-top: 16px;
}

.detail-title {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 10px;
  color: var(--text-primary);
}

.detail-item {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  font-size: 13px;
}

.detail-label {
  color: var(--text-secondary);
}

.detail-value {
  color: var(--text-primary);
  font-weight: 500;
}

.invite-card {
  margin-bottom: 20px;
}

.invite-section {
  margin-bottom: 16px;
}

.invite-code-area {
  margin-bottom: 12px;
}

.invite-code-label {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.invite-code-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.invite-code {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 2px;
  color: var(--el-color-primary);
  background: var(--bg-hover);
  padding: 4px 12px;
  border-radius: 6px;
}

.generate-btn {
  width: 100%;
}

.no-invite {
  text-align: center;
  padding: 16px 0;
  color: var(--text-muted);
  font-size: 13px;
}

.invited-users {
  border-top: 1px solid var(--border-light);
  padding-top: 12px;
}

.invited-title {
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 8px;
  color: var(--text-primary);
}

.invited-user-item {
  padding: 8px 0;
  border-bottom: 1px solid var(--border-light);
}

.invited-user-item:last-child {
  border-bottom: none;
}

.invited-email {
  font-size: 13px;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.invited-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-muted);
}

.recent-card {
  margin-bottom: 20px;
}
</style>