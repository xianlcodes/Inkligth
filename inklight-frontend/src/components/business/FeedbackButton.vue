<template>
  <div class="feedback-trigger">
    <el-button type="primary" circle class="feedback-fab" @click="dialogVisible = true">
      <el-icon :size="20"><ChatDotRound /></el-icon>
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
import { ref } from 'vue'
import { ChatDotRound } from '@element-plus/icons-vue'
import { submitFeedback } from '@/api/feedback'
import { ElMessage } from 'element-plus'

const dialogVisible = ref(false)
const content = ref('')
const submitting = ref(false)

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
  right: 24px;
  bottom: 24px;
  z-index: 999;
}

.feedback-fab {
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.15);
  transition: transform 0.2s;
}

.feedback-fab:hover {
  transform: scale(1.1);
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
