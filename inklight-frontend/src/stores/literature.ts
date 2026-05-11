import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import {
  getLiteratures,
  uploadLiterature,
  getLiterature,
  updateLiteratureStatus,
  type Literature,
  type LiteratureQuery,
} from '@/api/literature'

export const useLiteratureStore = defineStore('literature', () => {
  const literatures = ref<Literature[]>([])
  const total = ref(0)
  const loading = ref(false)
  const currentLiterature = ref<Literature | null>(null)

  const query = ref<LiteratureQuery>({
    skip: 0,
    limit: 20,
    title: '',
    status: '',
    sort_by_year: '',
  })

  async function fetchLiteratures(params?: LiteratureQuery) {
    loading.value = true
    try {
      const merged = { ...query.value, ...params }
      const res = await getLiteratures(merged)
      literatures.value = res.data.items
      total.value = res.data.total
    } finally {
      loading.value = false
    }
  }

  async function upload(file: File) {
    const res = await uploadLiterature(file)
    literatures.value.unshift(res.data)
    total.value += 1
    return res.data
  }

  async function fetchLiteratureDetail(id: string) {
    const res = await getLiterature(id)
    currentLiterature.value = res.data
    return res.data
  }

  async function updateStatus(id: string, status: string) {
    const res = await updateLiteratureStatus(id, status)
    const idx = literatures.value.findIndex((l) => l.id === id)
    if (idx !== -1) {
      literatures.value[idx] = res.data
    }
    if (currentLiterature.value?.id === id) {
      currentLiterature.value = res.data
    }
    return res.data
  }

  return {
    literatures,
    total,
    loading,
    currentLiterature,
    query,
    fetchLiteratures,
    upload,
    fetchLiteratureDetail,
    updateStatus,
  }
})
