<template>
  <div class="notes-container">
    <div class="notes-header">
      <h2 class="notes-title">文献笔记</h2>
      <p class="notes-subtitle">管理所有文献的笔记与标注</p>
    </div>

    <div class="notes-filter">
      <el-select
        v-model="filterType"
        placeholder="笔记类型"
        clearable
        size="default"
        class="filter-select"
        @change="fetchNotes"
      >
        <el-option label="全部类型" value="" />
        <el-option label="通用笔记" value="general" />
        <el-option label="创新点" value="innovation" />
        <el-option label="方法" value="method" />
        <el-option label="问题" value="question" />
      </el-select>
      <el-input
        v-model="filterLiterature"
        placeholder="搜索文献标题..."
        clearable
        size="default"
        class="filter-input"
        @input="onFilterInput"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
    </div>

    <div v-loading="loading" class="notes-list">
      <el-empty v-if="!loading && filteredNotes.length === 0" description="暂无笔记" />

      <div
        v-for="note in filteredNotes"
        :key="note.id"
        class="note-card"
        @click="openEditDialog(note)"
      >
        <div class="note-card-left">
          <el-tag
            :type="noteTypeColor(note.note_type)"
            size="small"
            effect="dark"
            class="note-type-tag"
          >
            {{ noteTypeLabel(note.note_type) }}
          </el-tag>
        </div>
        <div class="note-card-body">
          <p class="note-quoted" v-if="note.quoted_text">{{ note.quoted_text }}</p>
          <p class="note-content" v-else-if="note.content">{{ note.content }}</p>
          <p class="note-empty" v-else>空笔记</p>
          <div class="note-meta">
            <span class="note-literature" v-if="note.literature_title">
              <el-icon><Document /></el-icon>
              {{ note.literature_title }}
            </span>
            <span class="note-date">{{ formatDate(note.created_at) }}</span>
          </div>
        </div>
        <div class="note-card-actions" @click.stop>
          <el-button
            text
            size="small"
            type="danger"
            @click="handleDelete(note)"
          >
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
      </div>
    </div>

    <!-- 编辑对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑笔记"
      width="640px"
      :close-on-click-modal="false"
    >
      <div class="edit-dialog-body">
        <div class="edit-meta">
          <span class="edit-literature" v-if="editingNote?.literature_title">
            <el-icon><Document /></el-icon>
            {{ editingNote.literature_title }}
          </span>
          <el-tag
            v-if="editingNote"
            :type="noteTypeColor(editingNote.note_type)"
            size="small"
            effect="dark"
          >
            {{ noteTypeLabel(editingNote.note_type) }}
          </el-tag>
        </div>
        <p class="edit-quoted" v-if="editingNote?.quoted_text">{{ editingNote.quoted_text }}</p>
        <div class="tiptap-wrapper">
          <div v-if="editor" class="tiptap-toolbar">
            <button
              v-for="(item, key) in toolbarItems"
              :key="key"
              class="toolbar-btn"
              :class="{ active: item.isActive() }"
              @click="item.action()"
              :title="item.title"
            >
              <component :is="item.icon" v-if="item.icon" />
              <span v-else>{{ item.label }}</span>
            </button>
          </div>
          <editor-content :editor="editor" class="tiptap-editor" />
        </div>
      </div>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch, shallowRef } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document, Delete, Search, Edit, Operation, Menu, Tickets } from '@element-plus/icons-vue'
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import UnderlineExtension from '@tiptap/extension-underline'
import Placeholder from '@tiptap/extension-placeholder'
import { getNotes, updateNote, deleteNote, type Note } from '@/api/note'

const notes = ref<Note[]>([])
const loading = ref(false)
const filterType = ref('')
const filterLiterature = ref('')
const editDialogVisible = ref(false)
const editingNote = ref<Note | null>(null)
const saving = ref(false)

const editor = useEditor({
  extensions: [
    StarterKit,
    UnderlineExtension,
    Placeholder.configure({ placeholder: '输入笔记内容...' }),
  ],
  content: '',
})

const toolbarItems = computed(() => {
  if (!editor.value) return []
  return {
    bold: {
      title: '加粗',
      icon: Edit,
      isActive: () => editor.value!.isActive('bold'),
      action: () => editor.value!.chain().focus().toggleBold().run(),
    },
    italic: {
      title: '斜体',
      icon: Operation,
      isActive: () => editor.value!.isActive('italic'),
      action: () => editor.value!.chain().focus().toggleItalic().run(),
    },
    underline: {
      title: '下划线',
      icon: Operation,
      isActive: () => editor.value!.isActive('underline'),
      action: () => editor.value!.chain().focus().toggleUnderline().run(),
    },
    bulletList: {
      title: '无序列表',
      icon: Menu,
      isActive: () => editor.value!.isActive('bulletList'),
      action: () => editor.value!.chain().focus().toggleBulletList().run(),
    },
  }
})

const filteredNotes = computed(() => {
  let result = notes.value
  if (filterLiterature.value) {
    const kw = filterLiterature.value.toLowerCase()
    result = result.filter(n =>
      (n.literature_title || '').toLowerCase().includes(kw)
    )
  }
  return result
})

let filterTimer: ReturnType<typeof setTimeout> | null = null

function onFilterInput() {
  if (filterTimer) clearTimeout(filterTimer)
  filterTimer = setTimeout(() => fetchNotes(), 300)
}

onMounted(() => {
  fetchNotes()
})

onBeforeUnmount(() => {
  editor.value?.destroy()
})

async function fetchNotes() {
  loading.value = true
  try {
    const res = await getNotes(undefined, filterType.value || undefined)
    notes.value = res.data.items
  } catch {
    notes.value = []
  } finally {
    loading.value = false
  }
}

function openEditDialog(note: Note) {
  editingNote.value = note
  editDialogVisible.value = true
  setTimeout(() => {
    editor.value?.commands.setContent(note.content || note.quoted_text || '')
  }, 50)
}

async function handleSave() {
  if (!editingNote.value || !editor.value) return
  saving.value = true
  try {
    const html = editor.value.getHTML()
    await updateNote(editingNote.value.id, { content: html })
    ElMessage.success('笔记已保存')
    editDialogVisible.value = false
    await fetchNotes()
  } catch (error: any) {
    const detail = error.response?.data?.detail || '保存失败'
    ElMessage.error(detail)
  } finally {
    saving.value = false
  }
}

async function handleDelete(note: Note) {
  try {
    await ElMessageBox.confirm('确定删除这条笔记？', '确认删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await deleteNote(note.id)
    ElMessage.success('笔记已删除')
    await fetchNotes()
  } catch (error: any) {
    const detail = error.response?.data?.detail || '删除失败'
    ElMessage.error(detail)
  }
}

function noteTypeLabel(type: string) {
  const map: Record<string, string> = {
    general: '通用',
    innovation: '创新',
    method: '方法',
    question: '问题',
  }
  return map[type] || type
}

function noteTypeColor(type: string) {
  const map: Record<string, string> = {
    general: '',
    innovation: 'success',
    method: 'warning',
    question: 'danger',
  }
  return map[type] || ''
}

function formatDate(dateStr: string) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.notes-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--bg-secondary);
}

.notes-header {
  padding: 24px 32px 16px;
  flex-shrink: 0;
}

.notes-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 4px 0;
}

.notes-subtitle {
  font-size: 13px;
  color: var(--text-muted);
  margin: 0;
}

.notes-filter {
  display: flex;
  gap: 12px;
  padding: 0 32px 16px;
  flex-shrink: 0;
}

.filter-select {
  width: 140px;
}

.filter-input {
  flex: 1;
  max-width: 320px;
}

.notes-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 32px 24px;
}

.note-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.note-card:hover {
  border-color: var(--accent-primary);
  box-shadow: 0 2px 12px rgba(13, 148, 136, 0.08);
}

.note-card-left {
  flex-shrink: 0;
  padding-top: 2px;
}

.note-type-tag {
  border-radius: var(--radius-lg);
}

.note-card-body {
  flex: 1;
  min-width: 0;
}

.note-quoted {
  font-size: 14px;
  color: var(--text-primary);
  line-height: 1.6;
  margin: 0 0 8px 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.note-content {
  font-size: 14px;
  color: var(--text-primary);
  line-height: 1.6;
  margin: 0 0 8px 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.note-empty {
  font-size: 13px;
  color: var(--text-muted);
  font-style: italic;
  margin: 0 0 8px 0;
}

.note-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.note-literature {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--accent-primary);
}

.note-date {
  font-size: 12px;
  color: var(--text-muted);
}

.note-card-actions {
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 0.2s;
}

.note-card:hover .note-card-actions {
  opacity: 1;
}

.edit-dialog-body {
  max-height: 60vh;
  overflow-y: auto;
}

.edit-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.edit-literature {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--accent-primary);
  font-weight: 500;
}

.edit-quoted {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
  padding: 10px 12px;
  background: var(--bg-tertiary);
  border-left: 3px solid var(--accent-primary);
  border-radius: var(--radius-md);
  margin: 0 0 14px 0;
}

.tiptap-wrapper {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.tiptap-toolbar {
  display: flex;
  gap: 2px;
  padding: 6px 8px;
  background: var(--bg-tertiary);
  border-bottom: 1px solid var(--border-color);
}

.toolbar-btn {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  transition: all 0.15s;
}

.toolbar-btn:hover {
  background: var(--bg-primary);
  color: var(--text-primary);
}

.toolbar-btn.active {
  background: var(--accent-primary);
  color: #fff;
}

.tiptap-editor {
  padding: 12px 14px;
  min-height: 160px;
  max-height: 300px;
  overflow-y: auto;
}

.tiptap-editor :deep(.ProseMirror) {
  outline: none;
  min-height: 160px;
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-primary);
}

.tiptap-editor :deep(.ProseMirror p.is-editor-empty:first-child::before) {
  content: attr(data-placeholder);
  color: var(--text-muted);
  pointer-events: none;
  float: left;
  height: 0;
}

.tiptap-editor :deep(.ProseMirror ul) {
  padding-left: 20px;
}

.tiptap-editor :deep(.ProseMirror li) {
  margin-bottom: 4px;
}
</style>