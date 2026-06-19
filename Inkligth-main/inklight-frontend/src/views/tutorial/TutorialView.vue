<template>
  <div class="mx-auto px-8 py-6" style="max-width:900px">
    <div class="mb-5">
      <el-button text @click="router.back()">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
    </div>

    <div v-if="loading" class="py-10">
      <el-skeleton :rows="10" animated />
    </div>

    <div v-else-if="!tutorial" class="py-10">
      <el-empty description="教程不存在或未发布">
        <el-button @click="router.push('/tutorials')">返回教程列表</el-button>
      </el-empty>
    </div>

    <article v-else class="bg-white rounded-xl px-8 py-8 shadow-xs border">
      <h1 class="text-3xl font-bold text-slate-800 m-0 mb-3">{{ tutorial.title }}</h1>
      <div class="flex flex-col gap-1 text-sm text-slate-500">
        <span>发布时间：{{ formatDateTime(tutorial.published_at) }}</span>
        <span v-if="tutorial.summary" class="italic">{{ tutorial.summary }}</span>
      </div>
      <el-divider />
      <div class="tutorial-content leading-relaxed text-base text-slate-800" v-html="tutorial.content"></div>
    </article>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { getPublishedTutorial, type TutorialDetail } from '@/api/tutorial'
import { formatDateTime } from '@/utils/time'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const tutorial = ref<TutorialDetail | null>(null)

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
.tutorial-content :deep(h1) { font-size: 2em; margin: 0.67em 0; }
.tutorial-content :deep(h2) { font-size: 1.5em; margin: 0.75em 0; }
.tutorial-content :deep(h3) { font-size: 1.17em; margin: 0.83em 0; }
.tutorial-content :deep(p) { margin: 0.5em 0; }
.tutorial-content :deep(ul), .tutorial-content :deep(ol) { padding-left: 1.5em; }
.tutorial-content :deep(li) { margin: 0.25em 0; }
.tutorial-content :deep(img) { max-width: 100%; height: auto; border-radius: var(--radius-sm); margin: 8px 0; }
.tutorial-content :deep(a) { color: var(--accent-primary); }
.tutorial-content :deep(blockquote) { border-left: 3px solid var(--border-color); padding-left: 12px; color: var(--text-secondary); margin: 12px 0; }
.tutorial-content :deep(code) { background: var(--bg-tertiary); padding: 2px 6px; border-radius: 3px; font-size: 0.9em; }
.tutorial-content :deep(pre) { background: var(--bg-tertiary); padding: 12px; border-radius: 6px; overflow-x: auto; }
.tutorial-content :deep(pre code) { background: none; padding: 0; }
.tutorial-content :deep(hr) { border: none; border-top: 1px solid var(--border-color); margin: 24px 0; }
.tutorial-content :deep(table) { border-collapse: collapse; width: 100%; margin: 12px 0; }
.tutorial-content :deep(th), .tutorial-content :deep(td) { border: 1px solid var(--border-color); padding: 8px 12px; text-align: left; }
.tutorial-content :deep(th) { background: var(--bg-tertiary); font-weight: 600; }
</style>