<template>
  <div class="tutorial-page max-w-5xl mx-auto py-6">
    <div class="section-bar">
      <div class="section-bar-line"></div>
      <h2 class="section-title">使用教程</h2>
      <span class="section-accent">GUIDES</span>
    </div>

    <div v-if="loading" class="py-10">
      <el-skeleton :rows="4" animated v-for="i in 3" :key="i" class="mb-4" />
    </div>

    <div v-else-if="tutorials.length === 0" class="py-10">
      <el-empty description="暂无已发布的教程" />
    </div>

    <div v-else class="grid gap-4" style="grid-template-columns:repeat(auto-fill,minmax(280px,1fr))">
      <el-card
        v-for="item in tutorials"
        :key="item.id"
        shadow="hover"
        class="cursor-pointer transition-all duration-200 hover:-translate-y-0_5"
        @click="router.push(`/tutorials/${item.id}`)"
      >
        <h3 class="text-lg font-semibold text-slate-800 m-0 mb-2">{{ item.title }}</h3>
        <p v-if="item.summary" class="text-sm text-slate-500 m-0 mb-3 line-clamp-2">{{ item.summary }}</p>
        <div class="text-xs text-slate-400">
          <span>{{ formatDateFull(item.published_at) }}</span>
        </div>
      </el-card>
    </div>

    <div v-if="total > pageSize" class="flex justify-center mt-6">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="fetchList"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listPublishedTutorials, type TutorialSummary } from '@/api/tutorial'
import { formatDateFull } from '@/utils/time'

const router = useRouter()
const loading = ref(true)
const tutorials = ref<TutorialSummary[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 12

async function fetchList() {
  loading.value = true
  try {
    const res = await listPublishedTutorials((currentPage.value - 1) * pageSize, pageSize)
    tutorials.value = res.data.items
    total.value = res.data.total
  } catch {
    tutorials.value = []
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchList()
})
</script>

<style scoped>
.tutorial-page {
  padding: 28px 32px 40px;
}
</style>
