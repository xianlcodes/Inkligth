<template>
  <div class="tutorial-view">
    <div class="tutorial-header">
      <el-button text @click="router.back()">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
    </div>

    <div v-if="loading" class="loading-wrap">
      <el-skeleton :rows="10" animated />
    </div>

    <div v-else-if="!tutorial" class="empty-wrap">
      <el-empty description="教程不存在或未发布">
        <el-button @click="router.push('/tutorials')">返回教程列表</el-button>
      </el-empty>
    </div>

    <article v-else class="tutorial-article">
      <h1 class="tutorial-title">{{ tutorial.title }}</h1>
      <div class="tutorial-meta">
        <span>发布时间：{{ formatDate(tutorial.published_at) }}</span>
        <span v-if="tutorial.summary" class="tutorial-summary">{{ tutorial.summary }}</span>
      </div>
      <el-divider />
      <div class="tutorial-content" v-html="tutorial.content"></div>
    </article>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { getPublishedTutorial, type TutorialDetail } from '@/api/tutorial'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const tutorial = ref<TutorialDetail | null>(null)

function formatDate(dateStr: string | null): string {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(async () => {
  const id = route.params.id as string
  try {
    const res = await getPublishedTutorial(id)
    tutorial.value = res.data
  } catch {
    tutorial.value = null
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.tutorial-view {
  max-width: 900px;
  margin: 0 auto;
  padding: 24px;
}

.tutorial-header {
  margin-bottom: 20px;
}

.loading-wrap,
.empty-wrap {
  padding: 40px 0;
}

.tutorial-article {
  background: var(--el-bg-color);
  border-radius: 8px;
  padding: 32px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

.tutorial-title {
  font-size: 28px;
  font-weight: 700;
  margin: 0 0 12px 0;
  color: var(--el-text-color-primary);
}

.tutorial-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

.tutorial-summary {
  color: var(--el-text-color-regular);
  font-style: italic;
}

.tutorial-content {
  line-height: 1.8;
  font-size: 16px;
  color: var(--el-text-color-primary);
}

.tutorial-content :deep(h1) { font-size: 2em; margin: 0.67em 0; }
.tutorial-content :deep(h2) { font-size: 1.5em; margin: 0.75em 0; }
.tutorial-content :deep(h3) { font-size: 1.17em; margin: 0.83em 0; }
.tutorial-content :deep(p) { margin: 0.5em 0; }
.tutorial-content :deep(ul), .tutorial-content :deep(ol) { padding-left: 1.5em; }
.tutorial-content :deep(li) { margin: 0.25em 0; }
.tutorial-content :deep(img) { max-width: 100%; height: auto; border-radius: 4px; margin: 8px 0; }
.tutorial-content :deep(a) { color: var(--el-color-primary); }
.tutorial-content :deep(blockquote) { border-left: 3px solid var(--el-border-color); padding-left: 12px; color: var(--el-text-color-secondary); margin: 12px 0; }
.tutorial-content :deep(code) { background: var(--el-fill-color); padding: 2px 6px; border-radius: 3px; font-size: 0.9em; }
.tutorial-content :deep(pre) { background: var(--el-fill-color); padding: 12px; border-radius: 6px; overflow-x: auto; }
.tutorial-content :deep(pre code) { background: none; padding: 0; }
.tutorial-content :deep(hr) { border: none; border-top: 1px solid var(--el-border-color); margin: 24px 0; }
.tutorial-content :deep(table) { border-collapse: collapse; width: 100%; margin: 12px 0; }
.tutorial-content :deep(th), .tutorial-content :deep(td) { border: 1px solid var(--el-border-color); padding: 8px 12px; text-align: left; }
.tutorial-content :deep(th) { background: var(--el-fill-color); font-weight: 600; }
</style>