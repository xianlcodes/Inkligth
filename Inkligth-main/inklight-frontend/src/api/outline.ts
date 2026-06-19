import apiClient from './client'

export interface SlideData {
  title: string
  bullets: string[]
  notes?: string
  page_type?: string
  visual_ref?: string | null
  suggested_chart?: string | null
  chart_data_hint?: string | null
}

export interface PPTTaskResponse {
  task_id: string
  task_type: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  total: number
  error: string | null
  slides?: SlideData[]
}

/** 启动后台 PPT 生成任务 */
export function startPPTGeneration(literatureId: string) {
  return apiClient.post<{ code: number; msg: string; data: { task_id: string } }>(
    `/literatures/${literatureId}/generate-ppt`,
  )
}

/** 获取 PPT 生成任务状态 */
export function getPPTStatus(literatureId: string, taskId: string) {
  return apiClient.get<PPTTaskResponse>(
    `/literatures/${literatureId}/generate-ppt/${taskId}`,
  )
}

/** 下载生成的 PPT 文件 */
export function downloadPPT(literatureId: string, taskId: string) {
  return apiClient.get(
    `/literatures/${literatureId}/generate-ppt/${taskId}/download`,
    { responseType: 'blob' },
  )
}
