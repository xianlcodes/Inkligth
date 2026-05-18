<template>
  <div class="tutorial-editor" v-if="editor">
    <div class="editor-toolbar">
      <button-group>
        <el-button size="small" @click="editor.chain().focus().toggleBold().run()" :type="editor.isActive('bold') ? 'primary' : 'default'">
          <strong>B</strong>
        </el-button>
        <el-button size="small" @click="editor.chain().focus().toggleItalic().run()" :type="editor.isActive('italic') ? 'primary' : 'default'">
          <em>I</em>
        </el-button>
        <el-button size="small" @click="editor.chain().focus().toggleUnderline().run()" :type="editor.isActive('underline') ? 'primary' : 'default'">
          <u>U</u>
        </el-button>
        <el-button size="small" @click="editor.chain().focus().toggleStrike().run()" :type="editor.isActive('strike') ? 'primary' : 'default'">
          <s>S</s>
        </el-button>
      </button-group>

      <el-divider direction="vertical" />

      <button-group>
        <el-button size="small" @click="editor.chain().focus().toggleHeading({ level: 1 }).run()" :type="editor.isActive('heading', { level: 1 }) ? 'primary' : 'default'">
          H1
        </el-button>
        <el-button size="small" @click="editor.chain().focus().toggleHeading({ level: 2 }).run()" :type="editor.isActive('heading', { level: 2 }) ? 'primary' : 'default'">
          H2
        </el-button>
        <el-button size="small" @click="editor.chain().focus().toggleHeading({ level: 3 }).run()" :type="editor.isActive('heading', { level: 3 }) ? 'primary' : 'default'">
          H3
        </el-button>
      </button-group>

      <el-divider direction="vertical" />

      <button-group>
        <el-button size="small" @click="editor.chain().focus().setTextAlign('left').run()" :type="editor.isActive({ textAlign: 'left' }) ? 'primary' : 'default'">
          左对齐
        </el-button>
        <el-button size="small" @click="editor.chain().focus().setTextAlign('center').run()" :type="editor.isActive({ textAlign: 'center' }) ? 'primary' : 'default'">
          居中
        </el-button>
        <el-button size="small" @click="editor.chain().focus().setTextAlign('right').run()" :type="editor.isActive({ textAlign: 'right' }) ? 'primary' : 'default'">
          右对齐
        </el-button>
      </button-group>

      <el-divider direction="vertical" />

      <button-group>
        <el-button size="small" @click="editor.chain().focus().toggleBulletList().run()" :type="editor.isActive('bulletList') ? 'primary' : 'default'">
          <el-icon><List /></el-icon>
        </el-button>
        <el-button size="small" @click="editor.chain().focus().toggleOrderedList().run()" :type="editor.isActive('orderedList') ? 'primary' : 'default'">
          <el-icon><Tickets /></el-icon>
        </el-button>
      </button-group>

      <el-divider direction="vertical" />

      <button-group>
        <el-button size="small" @click="insertLink">
          <el-icon><Link /></el-icon>
        </el-button>
        <el-button size="small" @click="triggerImageUpload">
          <el-icon><Picture /></el-icon>
        </el-button>
      </button-group>

      <input ref="imageInput" type="file" accept="image/jpeg,image/png,image/gif,image/webp" style="display: none" @change="handleImageUpload" />
    </div>

    <editor-content :editor="editor" class="editor-content" />
  </div>
</template>

<script setup lang="ts">
import { ref, onBeforeUnmount, watch } from 'vue'
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import { Underline } from '@tiptap/extension-underline'
import { TextAlign } from '@tiptap/extension-text-align'
import { Link as LinkExtension } from '@tiptap/extension-link'
import { Image as ImageExtension } from '@tiptap/extension-image'
import { Placeholder } from '@tiptap/extension-placeholder'
import { ElMessage, ElMessageBox } from 'element-plus'
import { List, Tickets, Link, Picture } from '@element-plus/icons-vue'
import { uploadTutorialImage } from '@/api/tutorial'

const props = defineProps<{
  modelValue: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const imageInput = ref<HTMLInputElement>()

const editor = useEditor({
  content: props.modelValue,
  extensions: [
    StarterKit.configure({
      heading: { levels: [1, 2, 3] },
    }),
    Underline,
    TextAlign.configure({ types: ['heading', 'paragraph'] }),
    LinkExtension.configure({
      openOnClick: false,
      HTMLAttributes: { target: '_blank', rel: 'noopener noreferrer' },
    }),
    ImageExtension.configure({
      HTMLAttributes: { class: 'tutorial-image' },
    }),
    Placeholder.configure({ placeholder: '开始编写教程内容...' }),
  ],
  onUpdate: ({ editor }) => {
    emit('update:modelValue', editor.getHTML())
  },
})

watch(
  () => props.modelValue,
  (val) => {
    if (editor.value && val !== editor.value.getHTML()) {
      editor.value.commands.setContent(val, false)
    }
  },
)

onBeforeUnmount(() => {
  editor.value?.destroy()
})

function triggerImageUpload() {
  imageInput.value?.click()
}

async function handleImageUpload(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  const maxSize = 5 * 1024 * 1024
  if (file.size > maxSize) {
    ElMessage.warning('图片大小不能超过 5MB')
    input.value = ''
    return
  }

  try {
    const res = await uploadTutorialImage(file)
    const url = res.data.data.url
    editor.value?.chain().focus().setImage({ src: url }).run()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '图片上传失败')
  } finally {
    input.value = ''
  }
}

function insertLink() {
  const previousUrl = editor.value?.getAttributes('link').href || ''
  ElMessageBox.prompt('请输入链接地址', '插入链接', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    inputValue: previousUrl,
    inputPattern: /^https?:\/\/.+/,
    inputErrorMessage: '请输入有效的 URL（以 http:// 或 https:// 开头）',
  }).then(({ value }) => {
    if (value) {
      editor.value?.chain().focus().extendMarkRange('link').setLink({ href: value }).run()
    }
  }).catch(() => {})
}
</script>

<style scoped>
.tutorial-editor {
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  background: var(--el-bg-color);
}

.editor-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  background: var(--el-fill-color-light);
  border-radius: 6px 6px 0 0;
}

.editor-toolbar button-group {
  display: flex;
  gap: 2px;
}

.editor-content {
  padding: 16px;
  min-height: 400px;
  max-height: 600px;
  overflow-y: auto;
}

.editor-content :deep(.ProseMirror) {
  outline: none;
  min-height: 400px;
}

.editor-content :deep(.ProseMirror p.is-editor-empty:first-child::before) {
  content: attr(data-placeholder);
  float: left;
  color: var(--el-text-color-placeholder);
  pointer-events: none;
  height: 0;
}

.editor-content :deep(h1) { font-size: 2em; margin: 0.67em 0; }
.editor-content :deep(h2) { font-size: 1.5em; margin: 0.75em 0; }
.editor-content :deep(h3) { font-size: 1.17em; margin: 0.83em 0; }
.editor-content :deep(ul), .editor-content :deep(ol) { padding-left: 1.5em; }
.editor-content :deep(img.tutorial-image) { max-width: 100%; height: auto; border-radius: 4px; margin: 8px 0; }
.editor-content :deep(a) { color: var(--el-color-primary); text-decoration: underline; }
.editor-content :deep(blockquote) { border-left: 3px solid var(--el-border-color); padding-left: 12px; color: var(--el-text-color-secondary); }
.editor-content :deep(code) { background: var(--el-fill-color); padding: 2px 6px; border-radius: 3px; font-size: 0.9em; }
.editor-content :deep(pre) { background: var(--el-fill-color); padding: 12px; border-radius: 6px; overflow-x: auto; }
.editor-content :deep(pre code) { background: none; padding: 0; }
.editor-content :deep(hr) { border: none; border-top: 1px solid var(--el-border-color); margin: 16px 0; }
</style>