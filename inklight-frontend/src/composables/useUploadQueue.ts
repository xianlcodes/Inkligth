import { ref, computed, reactive } from 'vue'
import {
  initChunkUpload,
  uploadChunk,
  mergeChunks,
  pollTaskCompletion,
  getChunkSize,
} from '@/api/upload'

export type UploadStatus = 'pending' | 'uploading' | 'merging' | 'processing' | 'success' | 'failed' | 'paused' | 'cancelled'

export interface UploadItem {
  id: string
  file: File
  name: string
  size: number
  status: UploadStatus
  progress: number
  chunksTotal: number
  chunksDone: number
  literatureId: string | null
  taskId: string | null
  error: string | null
  retryCount: number
}

const MAX_BATCH_SIZE = 10
const MAX_CONCURRENT_UPLOADS = 2
const MAX_RETRIES = 2
const CHUNK_SIZE = getChunkSize()

function genId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

export function useUploadQueue() {
  const items = ref<UploadItem[]>([])
  const isUploading = ref(false)
  const stopFlags = new Map<string, boolean>()

  function createItem(file: File, folderId?: string): UploadItem {
    return {
      id: genId(),
      file,
      name: file.name,
      size: file.size,
      status: 'pending',
      progress: 0,
      chunksTotal: Math.ceil(file.size / CHUNK_SIZE),
      chunksDone: 0,
      literatureId: null,
      taskId: null,
      error: null,
      retryCount: 0,
    }
  }

  async function addFiles(files: File[], folderId?: string) {
    const pdfs = files.filter(
      (f) => f.type === 'application/pdf' || f.name.toLowerCase().endsWith('.pdf'),
    )
    if (pdfs.length !== files.length) {
      const nonPdf = files.filter(
        (f) => !(f.type === 'application/pdf' || f.name.toLowerCase().endsWith('.pdf')),
      )
      nonPdf.forEach((f) => {
        items.value.push({
          id: genId(),
          file: f,
          name: f.name,
          size: f.size,
          status: 'failed',
          progress: 0,
          chunksTotal: 0,
          chunksDone: 0,
          literatureId: null,
          taskId: null,
          error: '不支持的文件格式，仅支持 PDF',
          retryCount: 0,
        })
      })
    }

    if (items.value.length + pdfs.length > MAX_BATCH_SIZE) {
      const available = MAX_BATCH_SIZE - items.value.length
      if (available <= 0) return
      pdfs.splice(available)
    }

    items.value.push(...pdfs.map((f) => createItem(f, folderId)))
  }

  function removeItem(id: string) {
    const item = items.value.find((i) => i.id === id)
    if (item && (item.status === 'uploading' || item.status === 'merging')) {
      stopFlags.set(id, true)
    }
    items.value = items.value.filter((i) => i.id !== id)
  }

  function clearCompleted() {
    items.value = items.value.filter((i) => i.status !== 'success' && i.status !== 'failed' && i.status !== 'cancelled')
  }

  function pauseItem(id: string) {
    const item = items.value.find((i) => i.id === id)
    if (item && item.status === 'uploading') {
      stopFlags.set(id, true)
      item.status = 'paused'
    }
  }

  function resumeItem(id: string) {
    const item = items.value.find((i) => i.id === id)
    if (item && item.status === 'paused') {
      stopFlags.delete(id)
      item.status = 'pending'
      processQueue()
    }
  }

  function retryItem(id: string) {
    const item = items.value.find((i) => i.id === id)
    if (item && item.status === 'failed') {
      item.status = 'pending'
      item.progress = 0
      item.chunksDone = 0
      item.error = null
      item.taskId = null
      item.literatureId = null
      item.retryCount = 0
      processQueue()
    }
  }

  function startUpload() {
    processQueue()
  }

  async function processQueue() {
    isUploading.value = true

    while (true) {
      const active = items.value.filter((i) => i.status === 'uploading' || i.status === 'merging')
      const pending = items.value.filter((i) => i.status === 'pending')

      if (pending.length === 0 && active.length === 0) break
      if (active.length >= MAX_CONCURRENT_UPLOADS) break
      if (pending.length === 0) break

      const next = pending[0]
      next.status = 'uploading'
      processItem(next)
    }

    const remaining = items.value.filter(
      (i) => i.status === 'pending' || i.status === 'uploading' || i.status === 'merging' || i.status === 'processing' || i.status === 'paused',
    )
    if (remaining.length === 0) {
      isUploading.value = false
    }
  }

  async function processItem(item: UploadItem) {
    try {
      await uploadSingle(item)
    } catch {
      // handled in uploadSingle
    } finally {
      processQueue()
    }
  }

  async function uploadSingle(item: UploadItem) {
    const CHUNK_COUNT = Math.ceil(item.file.size / CHUNK_SIZE)

    try {
      // Step 1: Init
      if (stopFlags.get(item.id)) {
        item.status = 'paused'
        return
      }
      const initRes = await initChunkUpload(item.name, item.file.size, CHUNK_COUNT)
      const uploadId = initRes.upload_id
      item.chunksTotal = CHUNK_COUNT

      // Step 2: Upload chunks
      for (let i = 0; i < CHUNK_COUNT; i++) {
        if (stopFlags.get(item.id)) {
          item.status = 'paused'
          return
        }

        const start = i * CHUNK_SIZE
        const end = Math.min(start + CHUNK_SIZE, item.file.size)
        const blob = item.file.slice(start, end)

        let retries = 0
        while (retries <= MAX_RETRIES) {
          try {
            await uploadChunk(uploadId, i, blob)
            break
          } catch (e) {
            retries++
            if (retries > MAX_RETRIES) throw e
            await new Promise((r) => setTimeout(r, 1000 * retries))
          }
        }

        item.chunksDone = i + 1
        item.progress = Math.round(((i + 1) / CHUNK_COUNT) * 100)
      }

      if (stopFlags.get(item.id)) {
        item.status = 'paused'
        return
      }

      // Step 3: Merge
      item.status = 'merging'
      const mergeRes = await mergeChunks(uploadId)

      item.literatureId = mergeRes.literature_id !== 'pending' ? mergeRes.literature_id : null
      item.taskId = mergeRes.task_id || null

      if (mergeRes.literature_id && mergeRes.literature_id !== 'pending') {
        item.status = 'success'
        item.progress = 100
      } else if (mergeRes.task_id) {
        item.status = 'processing'
        try {
          const pollRes = await pollTaskCompletion(mergeRes.task_id, 1500, 300_000)
          if (pollRes.status === 'completed' && pollRes.result) {
            item.literatureId = String(pollRes.result.literature_id ?? '')
            item.status = 'success'
            item.progress = 100
          } else {
            item.error = pollRes.error || '元数据提取失败'
            item.status = 'failed'
          }
        } catch (pollErr: unknown) {
          item.error = pollErr instanceof Error ? pollErr.message : '处理超时'
          item.status = 'failed'
        }
      } else {
        item.status = 'success'
        item.progress = 100
      }
    } catch (e: unknown) {
      item.error = e instanceof Error ? e.message : '上传失败'
      item.status = 'failed'
      item.retryCount++
    }
  }

  const pendingCount = computed(() =>
    items.value.filter(
      (i) =>
        i.status === 'pending' ||
        i.status === 'uploading' ||
        i.status === 'merging' ||
        i.status === 'processing',
    ).length,
  )

  return reactive({
    items,
    isUploading,
    addFiles,
    removeItem,
    clearCompleted,
    pauseItem,
    resumeItem,
    retryItem,
    startUpload,
    pendingCount,
    MAX_BATCH_SIZE,
  })
}
