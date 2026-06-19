import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  fetchEngines,
  fetchEngine,
  createEngine,
  updateEngine,
  deleteEngine,
  testEngine,
  setDefaultEngine,
  type AIEngine,
  type AIEngineCreatePayload,
  type AIEngineUpdatePayload,
  type AIEngineTestResult,
} from '@/api/aiEngine'

export const useAiEngineStore = defineStore('aiEngine', () => {
  const engines = ref<AIEngine[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const defaultEngine = computed(() => engines.value.find((e) => e.is_default) || null)

  async function loadEngines() {
    loading.value = true
    error.value = null
    try {
      const res = await fetchEngines()
      engines.value = res.items
    } catch (e: any) {
      error.value = e?.response?.data?.detail || '加载引擎失败'
    } finally {
      loading.value = false
    }
  }

  async function addEngine(payload: AIEngineCreatePayload) {
    const created = await createEngine(payload)
    engines.value.unshift(created)
    if (created.is_default) {
      engines.value.forEach((e) => {
        if (e.id !== created.id) e.is_default = false
      })
    }
    return created
  }

  async function editEngine(engineId: string, payload: AIEngineUpdatePayload) {
    const updated = await updateEngine(engineId, payload)
    const idx = engines.value.findIndex((e) => e.id === engineId)
    if (idx !== -1) {
      engines.value[idx] = updated
    }
    if (updated.is_default) {
      engines.value.forEach((e) => {
        if (e.id !== updated.id) e.is_default = false
      })
    }
    return updated
  }

  async function removeEngine(engineId: string) {
    await deleteEngine(engineId)
    engines.value = engines.value.filter((e) => e.id !== engineId)
  }

  async function testConnection(engineId: string): Promise<AIEngineTestResult> {
    return await testEngine(engineId)
  }

  async function setAsDefault(engineId: string) {
    await setDefaultEngine(engineId)
    engines.value.forEach((e) => {
      e.is_default = e.id === engineId
    })
  }

  return {
    engines,
    loading,
    error,
    defaultEngine,
    loadEngines,
    addEngine,
    editEngine,
    removeEngine,
    testConnection,
    setAsDefault,
  }
})
