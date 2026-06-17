<template>
  <div class="admin-page">
    <div class="flex items-center justify-between mb-4">
      <div class="section-bar">
        <div class="section-bar-line"></div>
        <h2 class="section-title">用户反馈</h2>
        <span class="section-accent">FEEDBACK</span>
      </div>
      <div class="flex gap-2">
        <el-select v-model="filterResolved" placeholder="筛选状态" clearable style="width: 120px" @change="loadData">
          <el-option label="未处理" :value="false" />
          <el-option label="已处理" :value="true" />
        </el-select>
        <el-button @click="loadData">刷新</el-button>
      </div>
    </div>

    <el-table :data="items" v-loading="loading" stripe style="width: 100%">
      <el-table-column prop="user_name" label="用户名" width="120" />
      <el-table-column prop="user_email" label="邮箱" width="200" />
      <el-table-column prop="user_id" label="用户ID" width="100" show-overflow-tooltip>
        <template #default="{ row }">
          <code style="font-size:12px;color:var(--text-secondary)">{{ row.user_id.slice(0, 8) }}...</code>
        </template>
      </el-table-column>
      <el-table-column prop="content" label="反馈内容" min-width="300" show-overflow-tooltip />
      <el-table-column label="页面地址" width="180" show-overflow-tooltip>
        <template #default="{ row }">
          <a v-if="row.page_url" :href="row.page_url" target="_blank" class="page-link">
            {{ formatPageUrl(row.page_url) }}
          </a>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_resolved ? 'success' : 'warning'" size="small">
            {{ row.is_resolved ? '已处理' : '待处理' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="提交时间" width="180">
        <template #default="{ row }">
          {{ formatDateCN(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button v-if="!row.is_resolved" type="primary" link size="small" @click="handleResolve(row)">
            标记已处理
          </el-button>
          <span v-else style="color:var(--text-secondary);font-size:13px">已处理</span>
        </template>
      </el-table-column>
    </el-table>

    <div v-if="total > 0" class="flex justify-center mt-5">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        @current-change="loadData"
      />
    </div>

    <el-empty v-if="!loading && items.length === 0" description="暂无反馈" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listFeedback, resolveFeedback, type FeedbackItem } from '@/api/feedback'
import { ElMessage } from 'element-plus'
import { formatDateCN } from '@/utils/date'

const items = ref<FeedbackItem[]>([])
const total = ref(0)
const loading = ref(false)
const page = ref(1)
const pageSize = 20
const filterResolved = ref<boolean | undefined>(undefined)

function formatPageUrl(url: string): string {
  try {
    return new URL(url).pathname || url
  } catch {
    return url
  }
}

async function loadData() {
  loading.value = true
  try {
    const res = await listFeedback({
      skip: (page.value - 1) * pageSize,
      limit: pageSize,
      resolved: filterResolved.value,
    })
    items.value = res.data.items
    total.value = res.data.total
  } catch {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

async function handleResolve(row: FeedbackItem) {
  try {
    await resolveFeedback(row.id)
    ElMessage.success('已标记为已处理')
    await loadData()
  } catch {
    ElMessage.error('操作失败')
  }
}

onMounted(loadData)
</script>

<style scoped>
.admin-page {
  max-width: 1200px;
}

.section-bar {
  display: flex;
  align-items: center;
  gap: 14px;
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

.page-link {
  color: var(--accent-primary);
  text-decoration: none;
  font-size: 13px;
}
.page-link:hover {
  text-decoration: underline;
}
</style>
