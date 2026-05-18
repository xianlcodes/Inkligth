<template>
  <div class="tutorial-list-page">
    <div class="list-header">
      <h2>使用教程</h2>
    </div>

    <div v-if="loading" class="loading-wrap">
      <el-skeleton :rows="4" animated v-for="i in 3" :key="i" style="margin-bottom: 16px" />
    </div>

    <div v-else-if="tutorials.length === 0" class="empty-wrap">
      <el-empty description="暂无已发布的教程" />
    </div>

    <div v-else class="tutorial-grid">
      <el-card
        v-for="item in tutorials"
        :key="item.id"
        shadow="hover"
        class="tutorial-card"
        @click="router.push(`/tutorials/${item.id}`)"
      >
        <h3 class="card-title">{{ item.title }}</h3>
        <p class="card-summary" v-if="item.summary">{{ item.summary }}</p>
        <div class="card-meta">
          <span>{{ formatDate(item.published_at) }}</span>
        </div>
      </el-card>
    </div>

    <div class="pagination-wrap" v-if="total > pageSize">
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

const router = useRouter()
const loading = ref(true)
const tutorials = ref<TutorialSummary[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 12

function formatDate(dateStr: string | null): string {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

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
.tutorial-list-page {
  max-width: 960px;
  margin: 0 auto;
  padding: 24px;
}

.list-header {
  margin-bottom: 24px;
}

.list-header h2 {
  margin: 0;
  font-size: 22px;
}

.loading-wrap,
.empty-wrap {
  padding: 40px 0;
}

.tutorial-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.tutorial-card {
  cursor: pointer;
  transition: transform 0.2s;
}

.tutorial-card:hover {
  transform: translateY(-2px);
}

.card-title {
  margin: 0 0 8px 0;
  font-size: 17px;
}

.card-summary {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: var(--el-text-color-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-meta {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}

.pagination-wrap {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}
</style>