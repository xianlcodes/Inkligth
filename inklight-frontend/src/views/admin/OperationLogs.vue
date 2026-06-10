<template>
  <div style="max-width:1200px">
    <div class="page-header">
      <h2 class="text-xl font-bold text-slate-800 m-0">操作日志</h2>
    </div>

    <div class="flex gap-3 mb-4">
      <el-select v-model="filterAction" placeholder="操作类型" clearable style="width:150px" @change="loadLogs">
        <el-option label="更新用户" value="update_user" />
        <el-option label="修改配置" value="update_config" />
        <el-option label="所有操作" value="" />
      </el-select>
      <el-input
        v-model="filterUser"
        placeholder="搜索用户邮箱..."
        clearable
        style="width:260px"
        @change="loadLogs"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
    </div>

    <el-table :data="logs" v-loading="loading" stripe>
      <el-table-column prop="created_at" label="时间" width="160">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column prop="user_email" label="操作用户" min-width="160">
        <template #default="{ row }">{{ row.user_email || '系统' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="100" align="center">
        <template #default="{ row }">
          <el-tag size="small">{{ actionLabel(row.action) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="resource" label="资源" width="120">
        <template #default="{ row }">{{ row.resource || '-' }}</template>
      </el-table-column>
      <el-table-column prop="detail" label="详情" min-width="250">
        <template #default="{ row }">{{ row.detail || '-' }}</template>
      </el-table-column>
      <el-table-column prop="ip_address" label="IP" width="130">
        <template #default="{ row }">{{ row.ip_address || '-' }}</template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="80" align="center">
        <template #default="{ row }">
          <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
            {{ row.status === 'success' ? '成功' : '失败' }}
          </el-tag>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!loading && logs.length === 0" description="暂无日志" />

    <div class="flex justify-end mt-4">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="loadLogs"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { getOperationLogs, type OperationLog } from '@/api/admin'
import { formatDateCN } from '@/utils/date'

const logs = ref<OperationLog[]>([])
const loading = ref(false)
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(50)
const filterAction = ref('')
const filterUser = ref('')

function actionLabel(action: string) {
  const map: Record<string, string> = {
    update_user: '更新用户', update_config: '修改配置',
  }
  return map[action] || action
}

const formatDate = formatDateCN

async function loadLogs() {
  loading.value = true
  try {
    const params: { skip: number; limit: number; action?: string; user_id?: string } = {
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value,
    }
    if (filterAction.value) params.action = filterAction.value
    const resp = await getOperationLogs(params)
    logs.value = resp.data.items
    total.value = resp.data.total
  } catch { logs.value = [] }
  finally { loading.value = false }
}

onMounted(() => { loadLogs() })
</script>

<style scoped>
</style>
