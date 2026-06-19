<template>
  <div class="admin-page">
    <div class="section-bar">
      <div class="section-bar-line"></div>
      <h2 class="section-title">用户管理</h2>
      <span class="section-accent">USERS</span>
    </div>

    <div class="table-toolbar">
      <el-input
        v-model="searchQuery"
        placeholder="搜索邮箱..."
        clearable
        class="search-input"
        @change="loadUsers"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <span class="toolbar-hint">共 {{ total }} 个用户</span>
    </div>

    <div class="table-wrap">
      <el-table :data="users" v-loading="loading" stripe class="user-table">
        <el-table-column prop="email" label="邮箱" min-width="180" show-overflow-tooltip />
        <el-table-column prop="username" label="用户名" width="100" show-overflow-tooltip>
          <template #default="{ row }">{{ row.username || '-' }}</template>
        </el-table-column>
        <el-table-column prop="literature_count" label="文献数" width="80" align="center" />
        <el-table-column prop="is_admin" label="管理员" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_admin ? 'danger' : 'info'" size="small">
              {{ row.is_admin ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间" width="170">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="last_login_at" label="最后登录" width="170">
          <template #default="{ row }">{{ formatDate(row.last_login_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="220" align="center">
          <template #default="{ row }">
            <el-button size="small" text type="primary" @click="openEditUser(row)">
              <el-icon><Edit /></el-icon>
              编辑
            </el-button>
            <el-button
              size="small"
              text
              :type="row.is_admin ? 'warning' : 'success'"
              @click="toggleAdmin(row)"
            >
              {{ row.is_admin ? '取消管理员' : '设为管理员' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="table-footer">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="loadUsers"
      />
    </div>

    <el-dialog v-model="dialogVisible" title="编辑用户" width="400px">
      <el-form :model="editForm" label-position="top">
        <el-form-item label="邮箱">
          <el-input :model-value="editingUser?.email" disabled />
        </el-form-item>
        <el-form-item label="新密码（留空不修改）">
          <el-input v-model="editForm.password" type="password" show-password placeholder="输入新密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Edit } from '@element-plus/icons-vue'
import { getAdminUsers, updateAdminUser, type AdminUser } from '@/api/admin'
import { formatDateCN } from '@/utils/date'

const users = ref<AdminUser[]>([])
const loading = ref(false)
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(50)
const searchQuery = ref('')

const dialogVisible = ref(false)
const editingUser = ref<AdminUser | null>(null)
const editForm = ref({ password: '' })
const submitting = ref(false)

async function loadUsers() {
  loading.value = true
  try {
    const resp = await getAdminUsers({
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value,
      search: searchQuery.value,
    })
    users.value = resp.data.items
    total.value = resp.data.total
  } catch {
    users.value = []
  } finally {
    loading.value = false
  }
}

function openEditUser(user: AdminUser) {
  editingUser.value = user
  editForm.value = { password: '' }
  dialogVisible.value = true
}

async function toggleAdmin(user: AdminUser) {
  const action = user.is_admin ? '取消管理员' : '设为管理员'
  const confirmed = await ElMessageBox.confirm(
    `确定要${action} ${user.email} 吗？`,
    '提示',
    { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
  ).catch(() => false)
  if (!confirmed) return

  try {
    await updateAdminUser(user.id, { is_admin: !user.is_admin })
    ElMessage.success(`${action}成功`)
    loadUsers()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

async function handleEdit() {
  if (!editingUser.value) return
  submitting.value = true
  try {
    const payload: { password?: string } = {}
    if (editForm.value.password) payload.password = editForm.value.password
    await updateAdminUser(editingUser.value.id, payload)
    ElMessage.success('用户已更新')
    dialogVisible.value = false
    loadUsers()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '更新失败')
  } finally {
    submitting.value = false
  }
}

const formatDate = formatDateCN

onMounted(() => {
  loadUsers()
})
</script>

<style scoped>
/* ── Toolbar ── */
.table-toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.search-input {
  width: 280px;
}

.search-input :deep(.el-input__wrapper) {
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  background: var(--bg-overlay);
  box-shadow: none !important;
}

.search-input :deep(.el-input__wrapper:hover) {
  border-color: var(--sky-300);
  background: var(--bg-overlay-hover);
}

.search-input :deep(.el-input__wrapper.is-focus) {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 3px rgba(2, 132, 199, 0.1) !important;
  background: var(--bg-overlay-heavy);
}

.toolbar-hint {
  font-size: 13px;
  color: var(--text-muted);
}

/* ── Table wrapper ── */
.table-wrap {
  border-radius: var(--radius-xl);
  overflow: hidden;
  border: 1px solid var(--border-color);
  background: var(--bg-overlay);
}

/* ── Table ── */
.user-table {
  --el-table-border-color: transparent;
}

.user-table :deep(.el-table__header-wrapper th) {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  background: var(--bg-overlay);
  border-bottom: 1px solid var(--border-color);
  padding: 14px 0;
  letter-spacing: 0.02em;
}

.user-table :deep(.el-table__body-wrapper td) {
  font-size: 14px;
  color: var(--text-primary);
  padding: 12px 0;
}

.user-table :deep(.el-table__body tr) {
  transition: background 0.15s;
}

.user-table :deep(.el-table__body tr:hover > td) {
  background: var(--bg-overlay-hover) !important;
}

.user-table :deep(.el-table__row--striped td) {
  background: rgba(0, 0, 0, 0.012);
}

/* ── Footer ── */
.table-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
