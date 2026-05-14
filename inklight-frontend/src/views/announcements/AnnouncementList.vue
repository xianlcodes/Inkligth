<template>
  <div class="announcement-list-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">系统公告</h1>
        <p class="page-subtitle">查看平台最新通知和公告</p>
      </div>
      <el-button
        v-if="authStore.user?.is_admin"
        type="primary"
        @click="openCreateDialog"
      >
        <el-icon><Plus /></el-icon>
        发布公告
      </el-button>
    </div>

    <div v-loading="loading" class="announcement-list">
      <el-empty v-if="!loading && announcements.length === 0" description="暂无公告" :image-size="80" />
      <div
        v-for="item in announcements"
        :key="item.id"
        class="announcement-card"
        :class="{
          'is-pinned': item.is_pinned,
          [`level-${item.level}`]: true,
        }"
      >
        <div class="card-header" @click="toggleExpand(item.id)">
          <div class="card-header-left">
            <el-icon v-if="item.is_pinned" class="pin-icon"><Top /></el-icon>
            <el-tag
              :type="levelTagType(item.level)"
              size="small"
              effect="plain"
              class="level-tag"
            >
              {{ levelLabel(item.level) }}
            </el-tag>
            <el-tag
              v-if="item.scope === 'site_wide'"
              type="danger"
              size="small"
              effect="plain"
              class="scope-tag"
            >
              全站
            </el-tag>
            <span class="card-title">{{ item.title }}</span>
          </div>
          <div class="card-header-right">
            <span v-if="!item.is_published" class="draft-badge">草稿</span>
            <span class="card-time">{{ formatDate(item.created_at) }}</span>
            <el-icon class="expand-icon" :class="{ expanded: expandedIds.has(item.id) }">
              <ArrowDown />
            </el-icon>
          </div>
        </div>
        <div v-if="expandedIds.has(item.id)" class="card-body">
          <div class="card-content">{{ item.content }}</div>
          <div v-if="item.expires_at" class="card-expiry">
            有效期至：{{ formatDateTime(item.expires_at) }}
          </div>
          <div v-if="authStore.user?.is_admin" class="card-actions">
            <el-button text size="small" type="primary" @click="openEditDialog(item)">
              <el-icon><Edit /></el-icon>
              编辑
            </el-button>
            <el-popconfirm
              title="确定要删除此公告吗？"
              confirm-button-text="删除"
              cancel-button-text="取消"
              @confirm="handleDelete(item.id)"
            >
              <template #reference>
                <el-button text size="small" type="danger">
                  <el-icon><Delete /></el-icon>
                  删除
                </el-button>
              </template>
            </el-popconfirm>
          </div>
        </div>
      </div>
    </div>

    <el-drawer
      v-model="drawerVisible"
      :title="editingId ? '编辑公告' : '发布公告'"
      size="480px"
    >
      <el-form :model="form" label-position="top" class="announcement-form">
        <el-form-item label="标题" required>
          <el-input v-model="form.title" placeholder="输入公告标题" maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="内容" required>
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="8"
            placeholder="输入公告内容（支持 Markdown）"
          />
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
            <el-radio value="site_wide">全站可见（含登录页）</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="是否置顶">
          <el-switch v-model="form.is_pinned" />
        </el-form-item>
        <el-form-item label="是否发布">
          <el-switch v-model="form.is_published" />
        </el-form-item>
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
          {{ editingId ? '保存修改' : '发布' }}
        </el-button>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Top, ArrowDown, Edit, Delete } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import {
  getAnnouncements,
  createAnnouncement,
  updateAnnouncement,
  deleteAnnouncement,
  type Announcement,
} from '@/api/announcement'

const authStore = useAuthStore()

const loading = ref(false)
const announcements = ref<Announcement[]>([])
const expandedIds = ref(new Set<string>())

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

onMounted(() => {
  loadAnnouncements()
})

async function loadAnnouncements() {
  loading.value = true
  try {
    const resp = await getAnnouncements()
    announcements.value = resp.data.items
  } catch {
    announcements.value = []
  } finally {
    loading.value = false
  }
}

function toggleExpand(id: string) {
  if (expandedIds.value.has(id)) {
    expandedIds.value.delete(id)
  } else {
    expandedIds.value.add(id)
  }
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
  if (!form.value.title.trim() || !form.value.content.trim()) {
    ElMessage.warning('标题和内容不能为空')
    return
  }

  submitting.value = true
  try {
    const payload = {
      ...form.value,
      expires_at: form.value.expires_at || undefined,
    }
    if (editingId.value) {
      await updateAnnouncement(editingId.value, payload)
      ElMessage.success('公告已更新')
    } else {
      await createAnnouncement(payload as any)
      ElMessage.success('公告已发布')
    }
    drawerVisible.value = false
    await loadAnnouncements()
  } catch (error: any) {
    const detail = error.response?.data?.detail || '操作失败'
    ElMessage.error(detail)
  } finally {
    submitting.value = false
  }
}

async function handleDelete(id: string) {
  try {
    await deleteAnnouncement(id)
    ElMessage.success('公告已删除')
    expandedIds.value.delete(id)
    await loadAnnouncements()
  } catch (error: any) {
    const detail = error.response?.data?.detail || '删除失败'
    ElMessage.error(detail)
  }
}

function levelTagType(level: string) {
  const map: Record<string, string> = {
    info: '',
    warning: 'warning',
    success: 'success',
  }
  return map[level] || ''
}

function levelLabel(level: string) {
  const map: Record<string, string> = {
    info: '通知',
    warning: '提醒',
    success: '好消息',
  }
  return map[level] || level
}

function formatDate(dateStr: string) {
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

function formatDateTime(dateStr: string) {
  const d = new Date(dateStr)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}
</script>

<style scoped>
.announcement-list-page {
  padding: 32px;
  max-width: 900px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 28px;
}

.page-title {
  font-size: 26px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 4px 0;
}

.page-subtitle {
  font-size: 14px;
  color: var(--text-tertiary);
  margin: 0;
}

.announcement-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.announcement-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  overflow: hidden;
  transition: all 0.2s;
}

.announcement-card:hover {
  box-shadow: var(--shadow-md);
}

.announcement-card.is-pinned {
  border-color: var(--accent-primary);
  background: var(--teal-50);
}

.announcement-card.level-warning {
  border-left: 3px solid var(--warning, #e6a23c);
}

.announcement-card.level-success {
  border-left: 3px solid var(--success, #67c23a);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  cursor: pointer;
  user-select: none;
}

.card-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.pin-icon {
  color: var(--accent-primary);
  flex-shrink: 0;
}

.level-tag {
  flex-shrink: 0;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-header-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.draft-badge {
  font-size: 12px;
  color: var(--text-muted);
  background: var(--bg-tertiary);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
}

.card-time {
  font-size: 13px;
  color: var(--text-muted);
}

.expand-icon {
  transition: transform 0.2s;
}

.expand-icon.expanded {
  transform: rotate(180deg);
}

.card-body {
  padding: 0 20px 20px;
  border-top: 1px solid var(--border-color);
  padding-top: 16px;
}

.card-content {
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-secondary);
  white-space: pre-wrap;
  word-break: break-word;
}

.card-expiry {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 12px;
}

.card-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-color);
}

.announcement-form {
  padding: 8px 0;
}
</style>
