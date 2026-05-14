import apiClient from './client'

export interface ChunkInitResponse {
  upload_id: string
  chunk_size: number
}

export interface ChunkUploadResponse {
  upload_id: string
  chunk_index: number
  received: number
}

export interface ChunkMergeResponse {
  literature_id: string
  task_id: string | null
  message: string
}

export interface TaskStatusResponse {
  task_id: string
  task_type: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress: number
  total: number
  result: Record<string, unknown> | null
  error: string | null
}

const CHUNK_SIZE = 2 * 1024 * 1024

export function getChunkSize(): number {
  return CHUNK_SIZE
}

export async function initChunkUpload(
  filename: string,
  fileSize: number,
  totalChunks: number,
  folderId?: string,
): Promise<ChunkInitResponse> {
  const formData = new FormData()
  formData.append('filename', filename)
  formData.append('file_size', String(fileSize))
  formData.append('total_chunks', String(totalChunks))
  formData.append('chunk_size', String(CHUNK_SIZE))
  if (folderId) {
    formData.append('folder_id', folderId)
  }
  const res = await apiClient.post<ChunkInitResponse>('/upload/chunks/init', formData)
  return res.data
}

export async function uploadChunk(
  uploadId: string,
  chunkIndex: number,
  chunkBlob: Blob,
  onProgress?: (percent: number) => void,
): Promise<ChunkUploadResponse> {
  const formData = new FormData()
  formData.append('chunk_index', String(chunkIndex))
  formData.append('file', chunkBlob, `chunk_${chunkIndex}`)
  const res = await apiClient.post<ChunkUploadResponse>(
    `/upload/chunks/${uploadId}`,
    formData,
    {
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          onProgress(Math.round((progressEvent.loaded / progressEvent.total) * 100))
        }
      },
    },
  )
  return res.data
}

export async function mergeChunks(uploadId: string): Promise<ChunkMergeResponse> {
  const res = await apiClient.post<ChunkMergeResponse>(`/upload/chunks/${uploadId}/merge`)
  return res.data
}

export async function getTaskStatus(taskId: string): Promise<TaskStatusResponse> {
  const res = await apiClient.get<TaskStatusResponse>(`/tasks/${taskId}`)
  return res.data
}

export async function pollTaskCompletion(
  taskId: string,
  intervalMs = 1500,
  maxWaitMs = 300_000,
): Promise<TaskStatusResponse> {
  const startTime = Date.now()
  while (Date.now() - startTime < maxWaitMs) {
    const status = await getTaskStatus(taskId)
    if (status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled') {
      return status
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs))
  }
  throw new Error('任务处理超时')
}
