<template>
  <div
    class="feedback-trigger"
    :style="{ top: posY + 'px' }"
    @mousedown.prevent="onDragStart"
  >
    <el-button type="primary" class="feedback-btn" @click="handleClick">
      <el-icon :size="18"><ChatDotRound /></el-icon>
    </el-button>

    <el-dialog v-model="dialogVisible" title="反馈建议" width="480px" top="25vh" :close-on-click-modal="false">
      <el-form @submit.prevent="handleSubmit">
        <p class="feedback-hint">
          遇到问题或有建议？请描述一下，我们会尽快处理。
        </p>
        <el-input
          v-model="content"
          type="textarea"
          :rows="5"
          maxlength="2000"
          show-word-limit
          placeholder="请描述你的问题或建议..."
        />
        <div class="feedback-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="handleSubmit">
            提交反馈
          </el-button>
        </div>
      </el-form>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ChatDotRound } from '@element-plus/icons-vue'
import { submitFeedback } from '@/api/feedback'
import { ElMessage } from 'element-plus'

const dialogVisible = ref(false)
const content = ref('')
const submitting = ref(false)

const posY = ref(0)
let dragging = false
let didDrag = false
let dragStartY = 0
let dragStartPos = 0

function clamp(y: number) {
  return Math.max(12, Math.min(window.innerHeight - 64, y))
}

function handleClick() {
  if (didDrag) return
  dialogVisible.value = true
}

function onDragStart(e: MouseEvent) {
  dragging = true
  didDrag = false
  dragStartY = e.clientY
  dragStartPos = posY.value
  document.addEventListener('mousemove', onDragMove)
  document.addEventListener('mouseup', onDragEnd)
}

function onDragMove(e: MouseEvent) {
  if (!dragging) return
  posY.value = clamp(dragStartPos + (e.clientY - dragStartY))
  if (Math.abs(e.clientY - dragStartY) > 5) {
    didDrag = true
  }
}

function onDragEnd() {
  dragging = false
  document.removeEventListener('mousemove', onDragMove)
  document.removeEventListener('mouseup', onDragEnd)
}

onMounted(() => {
  posY.value = clamp(window.innerHeight - 80)
})

onUnmounted(() => {
  document.removeEventListener('mousemove', onDragMove)
  document.removeEventListener('mouseup', onDragEnd)
})

async function handleSubmit() {
  if (!content.value.trim()) return
  submitting.value = true
  try {
    await submitFeedback({
      content: content.value.trim(),
      page_url: window.location.href,
      browser_info: navigator.userAgent.slice(0, 200),
    })
    ElMessage.success('感谢你的反馈！')
    dialogVisible.value = false
    content.value = ''
  } catch {
    ElMessage.error('提交失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.feedback-trigger {
  position: fixed;
  right: 0;
  z-index: 1000;
  cursor: grab;
  user-select: none;
}

.feedback-btn {
  border-radius: 8px 0 0 8px !important;
  padding: 14px 10px !important;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.18);
  display: flex;
  align-items: center;
  justify-content: center;
  border-right: none !important;
}

.feedback-btn:hover {
  transform: none;
}

.feedback-hint {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0 0 12px 0;
}

.feedback-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
}
</style>
