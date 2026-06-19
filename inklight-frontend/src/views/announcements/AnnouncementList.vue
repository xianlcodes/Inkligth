<template>
  <div class="announcements-page max-w-4xl mx-auto py-6">
    <div class="announcements-header flex items-center justify-between">
      <div class="section-bar">
        <div class="section-bar-line"></div>
        <h1 class="section-title">系统公告</h1>
        <span class="section-accent">NEWS</span>
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
    <p class="announcements-subtitle">查看平台最新通知和公告</p>

    <div v-loading="loading" class="flex flex-col gap-3">
      <el-empty v-if="!loading && announcements.length === 0" description="暂无公告" :image-size="80" />
      <div
        v-for="item in announcements"
        :key="item.id"
        class="bg-white border rounded-xl overflow-hidden transition-all duration-200 hover:shadow-md"
        :class="{
          'border-sky-500 bg-sky-50': item.is_pinned,
          'border-l-3 border-l-amber-500': item.level === 'warning',
          'border-l-3 border-l-emerald-500': item.level === 'success',
        }"
        :style="item.is_pinned ? { borderLeftColor: 'var(--accent-primary)' } : {}"
      >
        <div class="flex items-center justify-between px-5 py-4 cursor-pointer select-none" @click="toggleExpand(item.id)">
          <div class="flex items-center gap-2 min-w-0">
            <el-icon v-if="item.is_pinned" class="text-sky-600 flex-shrink-0"><Top /></el-icon>
            <el-tag :type="levelTagType(item.level)" size="small" effect="plain" class="flex-shrink-0">
              {{ levelLabel(item.level) }}
            </el-tag>
            <el-tag v-if="item.scope === 'site_wide'" type="danger" size="small" effect="plain" class="flex-shrink-0">
              全站
            </el-tag>
            <span class="text-base font-semibold text-slate-800 truncate">{{ item.title }}</span>
          </div>
          <div class="flex items-center gap-3 flex-shrink-0">
            <span v-if="!item.is_published" class="text-xs text-slate-400 bg-slate-100 px-2 py-0_5 rounded-xs">草稿</span>
            <span class="text-sm text-slate-400">{{ formatDateOnly(item.created_at) }}</span>
            <el-icon class="transition-all duration-200" :class="{ 'rotate-180': expandedIds.has(item.id) }">
              <ArrowDown />
            </el-icon>
          </div>
        </div>
        <div v-if="expandedIds.has(item.id)" class="px-5 pb-5 pt-4 border-t">
          <div class="text-sm text-slate-600 leading-relaxed whitespace-pre-wrap break-words">{{ item.content }}</div>
          <div v-if="item.expires_at" class="text-xs text-slate-400 mt-3">
            有效期至：{{ formatDateTime(item.expires_at) }}
          </div>
          <div v-if="authStore.user?.is_admin" class="flex gap-2 mt-3 pt-3 border-t">
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
      <el-form :model="form" label-position="top" class="py-2">
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
import { formatDateOnly, formatDateTime } from '@/utils/time'
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
    info: 'info',
    warning: 'warning',
    success: 'success',
  }
  return map[level] || 'info'
}

function levelLabel(level: string) {
  const map: Record<string, string> = {
    info: '通知',
    warning: '提醒',
    success: '好消息',
  }
  return map[level] || level
}
</script>