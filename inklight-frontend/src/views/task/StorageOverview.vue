<template>
  <div class="mx-auto" style="max-width:1100px">
    <div class="page-header">
      <h2 class="text-xl font-bold text-slate-800 m-0">个人空间</h2>
    </div>

    <el-row :gutter="20">
      <el-col :span="16">
        <el-card shadow="never">
          <template #header>
            <span class="text-base font-semibold text-slate-800">存储空间概览</span>
          </template>
          <div class="mb-5">
            <div class="flex gap-10 mb-4">
              <div class="flex flex-col gap-1">
                <span class="text-sm text-slate-500">总空间</span>
                <span class="text-2xl font-bold text-slate-800">{{ formatBytes(storage?.total_space) }}</span>
              </div>
              <div class="flex flex-col gap-1">
                <span class="text-sm text-slate-500">已用空间</span>
                <span class="text-2xl font-bold text-amber-500">{{ formatBytes(storage?.used_space) }}</span>
              </div>
              <div class="flex flex-col gap-1">
                <span class="text-sm text-slate-500">剩余空间</span>
                <span class="text-2xl font-bold text-emerald-600">{{ formatBytes(storage?.remaining_space) }}</span>
              </div>
            </div>
            <el-progress
              :percentage="usagePercent"
              :stroke-width="16"
              :color="progressColor"
              class="mb-2"
            />
          </div>

          <div class="border-t pt-4">
            <div class="text-sm font-medium mb-2_5 text-slate-800">空间来源明细</div>
            <div class="flex justify-between py-1_5 text-sm">
              <span class="text-slate-500">基础空间</span>
              <span class="text-slate-800 font-medium">{{ formatBytes(storage?.base_space) }}</span>
            </div>
            <div class="flex justify-between py-1_5 text-sm">
              <span class="text-slate-500">签到奖励</span>
              <span class="text-slate-800 font-medium">{{ formatBytes(storage?.check_in_bonus) }}</span>
            </div>
            <div class="flex justify-between py-1_5 text-sm">
              <span class="text-slate-500">邀请奖励</span>
              <span class="text-slate-800 font-medium">{{ formatBytes(storage?.invitation_bonus) }}</span>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card shadow="never">
          <template #header>
            <span class="text-base font-semibold text-slate-800">我的邀请</span>
          </template>
          <div class="mb-4">
            <div v-if="invitations?.codes.length" class="mb-3">
              <div class="text-sm text-slate-500 mb-1_5">邀请码</div>
              <div class="flex items-center gap-2">
                <code class="text-lg font-bold tracking-wider text-sky-600 bg-sky-50 px-3 py-1 rounded-md">{{ invitations.codes[0].code }}</code>
                <el-button size="small" type="primary" @click="copyCode">
                  <el-icon><CopyDocument /></el-icon>
                  复制
                </el-button>
              </div>
            </div>
            <div v-else class="text-center py-4 text-slate-400 text-sm">
              <p>暂无邀请码</p>
            </div>
            <el-button
              size="small"
              type="primary"
              :disabled="(invitations?.codes.length || 0) >= 5"
              :loading="generating"
              class="w-full"
              @click="handleGenerate"
            >
              生成邀请码
            </el-button>
          </div>

          <div v-if="invitations?.invited_users.length" class="border-t pt-3">
            <div class="text-sm font-medium mb-2 text-slate-800">已邀请用户</div>
            <div
              v-for="user in invitations.invited_users"
              :key="user.email"
              class="py-2 border-b last:border-b-0"
            >
              <div class="text-sm text-slate-800 mb-1">{{ user.email }}</div>
              <div class="flex items-center justify-between text-xs text-slate-400">
                <span>{{ formatDateFull(user.registered_at) }}</span>
                <el-tag :type="user.reward_granted ? 'success' : 'warning'" size="small">
                  {{ user.reward_granted ? '已发放' : '待发放' }}
                </el-tag>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="mb-5" shadow="never">
      <template #header>
        <span class="text-base font-semibold text-slate-800">最近上传文献</span>
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
            {{ formatDateFull(row.created_at) }}
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
import { formatDateFull } from '@/utils/time'

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
</style>