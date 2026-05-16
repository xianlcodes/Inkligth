<template>
  <div class="pre-meeting">
    <div class="page-header">
      <div>
        <h1 class="page-title">组会看板</h1>
        <p class="page-subtitle">管理汇报大纲，统一查看与下载</p>
      </div>
    </div>

    <div class="new-report-card">
      <div class="new-report-content">
        <div class="new-report-icon">
          <el-icon :size="28"><DataAnalysis /></el-icon>
        </div>
        <div class="new-report-info">
          <h3 class="new-report-title">准备新汇报</h3>
          <p class="new-report-sub">选择一篇文献，生成新的组会大纲</p>
        </div>
      </div>
      <div class="new-report-actions">
        <el-select
          v-model="selectedLiteratureId"
          placeholder="选择文献..."
          filterable
          clearable
          class="literature-select"
        >
          <el-option
            v-for="lit in literatureOptions"
            :key="lit.id"
            :label="lit.title || '未识别标题'"
            :value="lit.id"
          >
            <span>{{ lit.title || '未识别标题' }}</span>
            <span class="lit-option-author">{{ lit.authors }}</span>
          </el-option>
        </el-select>
        <el-button
          type="primary"
          :loading="generating"
          :disabled="!selectedLiteratureId"
          @click="handleGenerate"
        >
          <el-icon><MagicStick /></el-icon>
          生成大纲
        </el-button>
      </div>
    </div>

    <div v-if="generating" class="generating-bar">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>AI 正在分析文献并生成汇报大纲...</span>
    </div>

    <div v-if="generatedOutline" class="fresh-outline-card">
      <div class="fresh-outline-header">
        <el-icon :size="20" color="var(--teal-600)"><CircleCheck /></el-icon>
        <span>大纲已生成并保存</span>
      </div>
      <div class="fresh-outline-preview">
        <div
          v-for="(slide, idx) in generatedOutline.slides.slice(0, 3)"
          :key="idx"
          class="fresh-slide-chip"
        >
          <span class="fresh-slide-num">{{ idx + 1 }}</span>
          {{ slide.title }}
        </div>
        <span v-if="generatedOutline.slides.length > 3" class="fresh-slide-more">
          +{{ generatedOutline.slides.length - 3 }} 张
        </span>
      </div>
    </div>

    <div class="history-section">
      <div class="history-header">
        <h2 class="history-title">汇报历史</h2>
        <span class="history-count">共 {{ presentations.length }} 条记录</span>
      </div>

      <div v-loading="loading" class="history-list">
        <el-card
          v-for="pres in presentations"
          :key="pres.id"
          class="history-card"
          shadow="hover"
          @click="openPreview(pres)"
        >
          <div class="history-card-top">
            <div class="history-card-icon">
              <el-icon :size="20"><DataAnalysis /></el-icon>
            </div>
            <div class="history-card-info">
              <h4 class="history-card-title">{{ pres.literature_title || '未命名文献' }}</h4>
              <p class="history-card-meta">
                {{ pres.slide_count || '0 张幻灯片' }}
                <span class="meta-sep">·</span>
                {{ formatDate(pres.created_at) }}
              </p>
            </div>
          </div>
          <div class="history-card-actions" @click.stop>
            <el-button text type="primary" size="small" @click="openPreview(pres)">
              预览
            </el-button>
            <el-button text type="primary" size="small" @click="handleRegenerate(pres)">
              重新生成
            </el-button>
            <el-button text type="danger" size="small" @click="handleDelete(pres)">
              删除
            </el-button>
          </div>
        </el-card>

        <el-empty v-if="!loading && presentations.length === 0" description="暂无汇报记录，在上方选择文献生成第一条大纲" />
      </div>
    </div>

    <el-dialog
      v-model="previewVisible"
      :title="previewTitle"
      fullscreen
      :close-on-click-modal="false"
      destroy-on-close
    >
      <div v-if="previewSlides.length > 0" class="preview-body">
        <div class="preview-grid">
          <div
            v-for="(slide, idx) in previewSlides"
            :key="idx"
            class="preview-slide-card"
          >
            <div class="preview-slide-header">
              <span class="preview-slide-num">{{ idx + 1 }}</span>
              <span class="preview-slide-title">{{ slide.title }}</span>
            </div>
            <ul class="preview-slide-bullets">
              <li v-for="(bullet, bi) in slide.bullets" :key="bi">{{ bullet }}</li>
            </ul>
            <div v-if="slide.notes" class="preview-slide-notes">
              <el-icon><ChatLineSquare /></el-icon>
              <span>{{ slide.notes }}</span>
            </div>
          </div>
        </div>
      </div>
      <el-empty v-else description="暂无幻灯片" />

      <template #footer>
        <el-button @click="previewVisible = false">关闭</el-button>
        <el-button type="primary" :loading="downloading" @click="handleDownload">
          <el-icon><Download /></el-icon>
          下载 PPT
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DataAnalysis, MagicStick, Loading, CircleCheck, ChatLineSquare, Download } from '@element-plus/icons-vue'
import { getPresentations, deletePresentation, type PresentationItem } from '@/api/presentation'
import { getLiteratures, type Literature } from '@/api/literature'
import { generateOutline, downloadOutlinePptx, type OutlineData } from '@/api/outline'

const loading = ref(false)
const generating = ref(false)
const downloading = ref(false)
const presentations = ref<PresentationItem[]>([])
const selectedLiteratureId = ref('')
const literatureOptions = ref<Literature[]>([])
const generatedOutline = ref<OutlineData | null>(null)

const previewVisible = ref(false)
const previewTitle = ref('')
const previewSlides = ref<OutlineData['slides']>([])
const previewLiteratureId = ref('')

onMounted(() => {
  fetchPresentations()
  fetchAllLiterature()
})

async function fetchPresentations() {
  loading.value = true
  try {
    const resp = await getPresentations()
    presentations.value = resp.data.data.items
  } catch {
    presentations.value = []
  } finally {
    loading.value = false
  }
}

async function fetchAllLiterature() {
  try {
    const resp = await getLiteratures({ limit: 100 })
    literatureOptions.value = resp.data.items
  } catch {
    literatureOptions.value = []
  }
}

async function handleGenerate() {
  if (!selectedLiteratureId.value) return

  generating.value = true
  generatedOutline.value = null
  try {
    const resp = await generateOutline(selectedLiteratureId.value)
    generatedOutline.value = resp.data.data
    ElMessage.success('大纲已生成并保存')
    await fetchPresentations()
  } catch (error: any) {
    const detail = error.response?.data?.detail || '生成失败'
    ElMessage.error(detail)
  } finally {
    generating.value = false
  }
}

function openPreview(pres: PresentationItem) {
  previewTitle.value = pres.literature_title || '汇报大纲'
  previewSlides.value = pres.slides || []
  previewLiteratureId.value = pres.literature_id || ''
  previewVisible.value = true
}

async function handleRegenerate(pres: PresentationItem) {
  if (!pres.literature_id) {
    ElMessage.warning('该汇报未关联文献，无法重新生成')
    return
  }
  try {
    await ElMessageBox.confirm('重新生成将覆盖当前大纲，是否继续？', '确认', {
      confirmButtonText: '重新生成',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }

  generating.value = true
  generatedOutline.value = null
  try {
    const resp = await generateOutline(pres.literature_id)
    generatedOutline.value = resp.data.data
    ElMessage.success('大纲已重新生成')
    await fetchPresentations()
  } catch (error: any) {
    const detail = error.response?.data?.detail || '重新生成失败'
    ElMessage.error(detail)
  } finally {
    generating.value = false
  }
}

async function handleDelete(pres: PresentationItem) {
  try {
    await ElMessageBox.confirm('确定删除该汇报记录？', '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }

  try {
    await deletePresentation(pres.id)
    ElMessage.success('已删除')
    await fetchPresentations()
  } catch {
    ElMessage.error('删除失败')
  }
}

async function handleDownload() {
  if (!previewLiteratureId.value) {
    ElMessage.warning('该汇报未关联文献，无法下载 PPT')
    return
  }

  downloading.value = true
  try {
    const resp = await downloadOutlinePptx(previewLiteratureId.value)
    const blob = new Blob([resp.data], {
      type: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${previewTitle.value || 'presentation'}_outline.pptx`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    ElMessage.success('PPT 下载成功')
  } catch (error: any) {
    const detail = error.response?.data?.detail || '下载失败'
    ElMessage.error(detail)
  } finally {
    downloading.value = false
  }
}

function formatDate(dateStr: string) {
  const d = new Date(dateStr)
  return `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()}`
}
</script>

<style scoped>
.pre-meeting {
  padding: 32px;
  max-width: 1100px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 28px;
}

.page-title {
  font-size: 26px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 4px 0;
  letter-spacing: -0.5px;
}

.page-subtitle {
  font-size: 14px;
  color: var(--text-tertiary);
  margin: 0;
}

.new-report-card {
  background: linear-gradient(135deg, var(--teal-50) 0%, #ecfdf5 100%);
  border: 1px solid var(--teal-200);
  border-radius: var(--radius-2xl);
  padding: 28px 32px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
  margin-bottom: 24px;
}

.new-report-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.new-report-icon {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-xl);
  background: var(--teal-100);
  color: var(--teal-600);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.new-report-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 4px 0;
}

.new-report-sub {
  font-size: 13px;
  color: var(--text-tertiary);
  margin: 0;
}

.new-report-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.literature-select {
  width: 280px;
}

.lit-option-author {
  font-size: 12px;
  color: var(--text-muted);
  margin-left: 8px;
}

.generating-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 20px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  margin-bottom: 24px;
  font-size: 14px;
  color: var(--text-secondary);
}

.fresh-outline-card {
  background: var(--bg-primary);
  border: 1px solid var(--teal-200);
  border-radius: var(--radius-2xl);
  padding: 20px 24px;
  margin-bottom: 32px;
}

.fresh-outline-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--teal-700);
  margin-bottom: 12px;
}

.fresh-outline-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.fresh-slide-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: var(--teal-50);
  border-radius: 20px;
  font-size: 13px;
  color: var(--text-secondary);
}

.fresh-slide-num {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--teal-500);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.fresh-slide-more {
  display: flex;
  align-items: center;
  padding: 6px 14px;
  font-size: 13px;
  color: var(--text-muted);
}

.history-section {
  margin-top: 8px;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.history-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.history-count {
  font-size: 13px;
  color: var(--text-muted);
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.history-card {
  cursor: pointer;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  transition: all 0.2s;
}

.history-card:hover {
  border-color: var(--teal-200);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
}

.history-card-top {
  display: flex;
  align-items: center;
  gap: 14px;
}

.history-card-icon {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-lg);
  background: var(--teal-50);
  color: var(--teal-600);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.history-card-info {
  flex: 1;
  min-width: 0;
}

.history-card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 4px 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-card-meta {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0;
}

.meta-sep {
  margin: 0 6px;
}

.history-card-actions {
  display: flex;
  gap: 4px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-light);
}

.preview-body {
  padding: 16px 0;
}

.preview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 20px;
}

.preview-slide-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  padding: 24px;
  min-height: 180px;
}

.preview-slide-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 16px;
}

.preview-slide-num {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-md);
  background: var(--accent-primary);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.preview-slide-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.4;
}

.preview-slide-bullets {
  margin: 0;
  padding: 0 0 0 20px;
  list-style: none;
}

.preview-slide-bullets li {
  position: relative;
  font-size: 13px;
  line-height: 1.8;
  color: var(--text-secondary);
  padding: 2px 0;
}

.preview-slide-bullets li::before {
  content: '';
  position: absolute;
  left: -16px;
  top: 10px;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--teal-400);
}

.preview-slide-notes {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px dashed var(--border-color);
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.6;
}

.preview-slide-notes .el-icon {
  flex-shrink: 0;
  margin-top: 2px;
}
</style>