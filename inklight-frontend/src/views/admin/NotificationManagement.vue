<template>
  <div class="admin-page">
    <div class="flex items-center justify-between mb-4">
      <div class="section-bar">
        <div class="section-bar-line"></div>
        <h2 class="section-title">通知管理</h2>
        <span class="section-accent">NOTIFICATIONS</span>
      </div>
      <div class="flex gap-2">
        <el-button type="danger" plain size="small" :disabled="selectedIds.length === 0" @click="batchDelete">
          批量删除 ({{ selectedIds.length }})
        </el-button>
        <el-button type="primary" @click="openCreateDialog">
          <el-icon><Plus /></el-icon>
          发布通知
        </el-button>
      </div>
    </div>

    <div class="flex gap-3 mb-4">
      <el-select v-model="filterScope" placeholder="可见范围" clearable style="width:140px" @change="loadAnnouncements">
        <el-option label="全站可见" value="site_wide" />
        <el-option label="登录后可见" value="authenticated" />
      </el-select>
      <el-select v-model="filterPublished" placeholder="发布状态" clearable style="width:140px" @change="loadAnnouncements">
        <el-option label="已发布" :value="true" />
        <el-option label="草稿" :value="false" />
      </el-select>
    </div>

    <el-table
      :data="announcements"
      v-loading="loading"
      stripe
      @selection-change="(rows: any[]) => selectedIds = rows.map((r: any) => r.id)"
    >
      <el-table-column type="selection" width="50" />
      <el-table-column prop="title" label="标题" min-width="200" />
      <el-table-column label="级别" width="90" align="center">
        <template #default="{ row }">
          <el-tag :type="row.level === 'warning' ? 'warning' : row.level === 'success' ? 'success' : 'info'" size="small">
            {{ levelLabel(row.level) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="范围" width="90" align="center">
        <template #default="{ row }">
          <el-tag :type="row.scope === 'site_wide' ? 'danger' : ''" size="small">
            {{ row.scope === 'site_wide' ? '全站' : '登录后' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="80" align="center">
        <template #default="{ row }">
          <span :class="['status-badge', row.is_published ? 'published' : 'draft']">
            {{ row.is_published ? '已发布' : '草稿' }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="置顶" width="70" align="center">
        <template #default="{ row }">
          <el-icon v-if="row.is_pinned" color="var(--accent-primary)"><Top /></el-icon>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="160">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="260" align="center" fixed="right">
        <template #default="{ row }">
          <el-button size="small" text type="primary" @click="openEditDialog(row)">编辑</el-button>
          <el-button size="small" text :type="row.is_published ? 'warning' : 'success'" @click="togglePublish(row)">
            {{ row.is_published ? '撤回' : '发布' }}
          </el-button>
          <el-popconfirm title="确定删除？" @confirm="handleDelete(row.id)">
            <template #reference>
              <el-button size="small" text type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!loading && announcements.length === 0" description="暂无通知" />

    <el-drawer v-model="drawerVisible" :title="editingId ? '编辑通知' : '发布通知'" size="480px">
      <el-form :model="form" label-position="top">
        <el-form-item label="标题" required>
          <el-input v-model="form.title" placeholder="通知标题" maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="form.content" type="textarea" :rows="8" placeholder="通知内容" />
        </el-form-item>
        <el-form-item label="级别">
          <el-radio-group v-model="form.level">
            <el-radio value="info">通知</el-radio>
            <el-radio value="warning">提醒</el-radio>
            <el-radio value="success">好消息</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="可见范围">
          <el-radio-group v-model="form.scope">
            <el-radio value="authenticated">登录后可见</el-radio>
            <el-radio value="site_wide">全站可见</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="置顶">
              <el-switch v-model="form.is_pinned" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="发布">
              <el-switch v-model="form.is_published" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="过期时间（可选）">
          <el-date-picker
            v-model="form.expires_at"
            type="datetime"
            placeholder="选择过期时间"
            value-format="YYYY-MM-DDTHH:mm:ss"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="drawerVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ editingId ? '保存' : '发布' }}
        </el-button>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Top } from '@element-plus/icons-vue'
import { formatDateCN } from '@/utils/date'
import {
  getAnnouncements, createAnnouncement, updateAnnouncement, deleteAnnouncement,
  type Announcement,
} from '@/api/announcement'

const loading = ref(false)
const announcements = ref<Announcement[]>([])
const filterScope = ref('')
const filterPublished = ref<boolean | ''>('')
const selectedIds = ref<string[]>([])

const drawerVisible = ref(false)
const editingId = ref<string | null>(null)
const submitting = ref(false)

const defaultForm = () => ({
  title: '',
  content: '',
  level: 'info',
  scope: 'authenticated',
  is_pinned: false,
  is_published: true,
  expires_at: '',
})
const form = ref(defaultForm())

function levelLabel(level: string) {
  return { info: '通知', warning: '提醒', success: '好消息' }[level] || level
}

const formatDate = formatDateCN

async function loadAnnouncements() {
  loading.value = true
  try {
    const resp = await getAnnouncements()
    let items = resp.data.items
    if (filterScope.value) items = items.filter(a => a.scope === filterScope.value)
    if (filterPublished.value !== '') items = items.filter(a => a.is_published === filterPublished.value)
    announcements.value = items
  } catch {
    announcements.value = []
  } finally { loading.value = false }
}

function openCreateDialog() {
  editingId.value = null
  form.value = defaultForm()
  drawerVisible.value = true
}

function openEditDialog(item: Announcement) {
  editingId.value = item.id
  form.value = {
    title: item.title,
    content: item.content,
    level: item.level,
    scope: item.scope || 'authenticated',
    is_pinned: item.is_pinned,
    is_published: item.is_published,
    expires_at: item.expires_at || '',
  }
  drawerVisible.value = true
}

async function handleSubmit() {
  if (!form.value.title.trim()) { ElMessage.warning('标题不能为空'); return }
  submitting.value = true
  try {
    const payload = { ...form.value, expires_at: form.value.expires_at || undefined }
    if (editingId.value) {
      await updateAnnouncement(editingId.value, payload)
      ElMessage.success('通知已更新')
    } else {
      await createAnnouncement(payload)
      ElMessage.success('通知已发布')
    }
    drawerVisible.value = false
    loadAnnouncements()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally { submitting.value = false }
}

async function togglePublish(item: Announcement) {
  await updateAnnouncement(item.id, { is_published: !item.is_published })
  ElMessage.success(item.is_published ? '已撤回' : '已发布')
  loadAnnouncements()
}

async function handleDelete(id: string) {
  try {
    await deleteAnnouncement(id)
    ElMessage.success('已删除')
    loadAnnouncements()
  } catch { ElMessage.error('删除失败') }
}

async function batchDelete() {
  const confirmed = await ElMessageBox.confirm(
    `确定删除 ${selectedIds.value.length} 条通知？`,
    '批量删除',
    { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
  ).catch(() => false)
  if (!confirmed) return

  for (const id of selectedIds.value) {
    try { await deleteAnnouncement(id) } catch { /* skip */ }
  }
  ElMessage.success('批量删除完成')
  selectedIds.value = []
  loadAnnouncements()
}

onMounted(() => { loadAnnouncements() })
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

.status-badge {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
}

.status-badge.published {
  background: rgba(240,253,244,0.6);
  color: #16a34a;
}

.status-badge.draft {
  background: rgba(245,245,244,0.5);
  color: #78716c;
}
</style>
