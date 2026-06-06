<template>
  <div class="tutorial-manager">
    <div class="page-header">
      <h2>使用教程管理</h2>
      <el-button type="primary" @click="openCreate">新建教程</el-button>
    </div>

    <el-table v-loading="loading" :data="tutorials" stripe style="width: 100%">
      <el-table-column prop="title" label="标题" min-width="200">
        <template #default="{ row }">
          <span>{{ row.title }}</span>
          <el-tag v-if="row.is_published" type="success" size="small" style="margin-left: 8px">已发布</el-tag>
          <el-tag v-else type="info" size="small" style="margin-left: 8px">草稿</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="summary" label="摘要" min-width="250" show-overflow-tooltip />
      <el-table-column prop="version_count" label="版本数" width="80" align="center" />
      <el-table-column prop="updated_at" label="更新时间" width="170">
        <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
          <el-button link type="primary" size="small" @click="openVersions(row)">版本</el-button>
          <el-button
            link
            :type="row.is_published ? 'warning' : 'success'"
            size="small"
            @click="togglePublish(row)"
          >
            {{ row.is_published ? '取消发布' : '发布' }}
          </el-button>
          <el-popconfirm title="确定删除该教程？" @confirm="handleDelete(row.id)">
            <template #reference>
              <el-button link type="danger" size="small">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-wrap" v-if="total > pageSize">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="fetchTutorials"
      />
    </div>

    <el-dialog
      v-model="editorVisible"
      :title="editingTutorial ? '编辑教程' : '新建教程'"
      width="900px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-form :model="form" label-width="60px">
        <el-form-item label="标题" required>
          <el-input v-model="form.title" placeholder="教程标题" maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="摘要">
          <el-input v-model="form.summary" type="textarea" :rows="2" placeholder="可选摘要，发布后将在列表展示" maxlength="500" show-word-limit />
        </el-form-item>
        <el-form-item label="内容">
          <TutorialEditor v-model="form.content" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editorVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="versionsVisible" title="版本历史" width="800px">
      <el-timeline v-if="versions.length > 0">
        <el-timeline-item
          v-for="v in versions"
          :key="v.id"
          :timestamp="formatDate(v.created_at)"
          placement="top"
        >
          <el-card shadow="hover">
            <div class="version-header">
              <span class="version-number">版本 {{ v.version_number }}</span>
              <span class="version-title">{{ v.title }}</span>
            </div>
            <div class="version-summary" v-if="v.summary">{{ v.summary }}</div>
            <div class="version-actions">
              <el-button size="small" @click="previewVersion(v)">预览</el-button>
              <el-popconfirm title="恢复此版本将覆盖当前内容，确定恢复？" @confirm="handleRestore(v.id)">
                <template #reference>
                  <el-button size="small" type="primary">恢复此版本</el-button>
                </template>
              </el-popconfirm>
            </div>
          </el-card>
        </el-timeline-item>
      </el-timeline>
      <el-empty v-else description="暂无版本历史" />
    </el-dialog>

    <el-dialog v-model="previewVisible" title="版本预览" width="800px">
      <div class="preview-content" v-html="previewHtml"></div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import TutorialEditor from '@/components/business/TutorialEditor.vue'
import { formatDateCN } from '@/utils/date'
import {
  listTutorials,
  createTutorial,
  updateTutorial,
  deleteTutorial,
  listTutorialVersions,
  restoreTutorialVersion,
  type TutorialSummary,
  type TutorialDetail,
  type TutorialVersion,
} from '@/api/tutorial'

const loading = ref(false)
const saving = ref(false)
const tutorials = ref<TutorialSummary[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 20

const editorVisible = ref(false)
const editingTutorial = ref<TutorialDetail | null>(null)
const form = reactive({ title: '', summary: '', content: '' })

const versionsVisible = ref(false)
const versions = ref<TutorialVersion[]>([])
const activeTutorialId = ref('')

const previewVisible = ref(false)
const previewHtml = ref('')

const formatDate = (dateStr: string): string => {
  if (!dateStr) return ''
  return formatDateCN(dateStr)
}

async function fetchTutorials() {
  loading.value = true
  try {
    const res = await listTutorials((currentPage.value - 1) * pageSize, pageSize)
    tutorials.value = res.data.items
    total.value = res.data.total
  } catch {
    ElMessage.error('加载教程列表失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingTutorial.value = null
  form.title = ''
  form.summary = ''
  form.content = ''
  editorVisible.value = true
}

async function openEdit(row: TutorialSummary) {
  try {
    const { getTutorial } = await import('@/api/tutorial')
    const res = await getTutorial(row.id)
    editingTutorial.value = res.data
    form.title = res.data.title
    form.summary = res.data.summary || ''
    form.content = res.data.content
    editorVisible.value = true
  } catch {
    ElMessage.error('加载教程详情失败')
  }
}

async function handleSave() {
  if (!form.title.trim()) {
    ElMessage.warning('请输入教程标题')
    return
  }

  saving.value = true
  try {
    if (editingTutorial.value) {
      await updateTutorial(editingTutorial.value.id, {
        title: form.title,
        summary: form.summary || null,
        content: form.content,
      })
      ElMessage.success('教程已更新')
    } else {
      await createTutorial({
        title: form.title,
        summary: form.summary || null,
        content: form.content,
      })
      ElMessage.success('教程已创建')
    }
    editorVisible.value = false
    await fetchTutorials()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function togglePublish(row: TutorialSummary) {
  try {
    await updateTutorial(row.id, { is_published: !row.is_published })
    ElMessage.success(row.is_published ? '已取消发布' : '已发布')
    await fetchTutorials()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '操作失败')
  }
}

async function handleDelete(id: string) {
  try {
    await deleteTutorial(id)
    ElMessage.success('已删除')
    await fetchTutorials()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '删除失败')
  }
}

async function openVersions(row: TutorialSummary) {
  activeTutorialId.value = row.id
  versionsVisible.value = true
  try {
    const res = await listTutorialVersions(row.id)
    versions.value = res.data.items
  } catch {
    ElMessage.error('加载版本历史失败')
  }
}

function previewVersion(v: TutorialVersion) {
  previewHtml.value = v.content
  previewVisible.value = true
}

async function handleRestore(versionId: string) {
  try {
    await restoreTutorialVersion(activeTutorialId.value, versionId)
    ElMessage.success('版本已恢复')
    versionsVisible.value = false
    await fetchTutorials()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '恢复失败')
  }
}

onMounted(() => {
  fetchTutorials()
})
</script>

<style scoped>
.tutorial-manager {
  padding: 4px 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
}

.pagination-wrap {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.version-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.version-number {
  font-weight: 600;
  color: var(--el-color-primary);
}

.version-title {
  font-size: 15px;
}

.version-summary {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  margin-bottom: 8px;
}

.version-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.preview-content {
  max-height: 60vh;
  overflow-y: auto;
  padding: 16px;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  background: var(--el-bg-color);
}

.preview-content :deep(img) {
  max-width: 100%;
  height: auto;
}
</style>