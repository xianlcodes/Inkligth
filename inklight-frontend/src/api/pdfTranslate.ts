import apiClient from './client'

export interface PdfTranslateResponse {
  task_id: string
  status: string
  message: string
}

export interface PdfTranslateTaskStatus {
  task_id: string
  status: string
  progress: number
  message: string
  download_url: string | null
  preview_url: string | null
}

export function startPdfTranslate(
  literatureId: string,
  sourceLang: string = 'en',
  targetLang: string = 'zh',
  outputMode: string = 'mono',
) {
  return apiClient.post<PdfTranslateResponse>(
    `/literatures/${literatureId}/translate-pdf`,
    null,
    {
      params: { source_lang: sourceLang, target_lang: targetLang, output_mode: outputMode },
    }
  )
}

export function getPdfTranslateStatus(literatureId: string, taskId: string) {
  return apiClient.get<PdfTranslateTaskStatus>(
    `/literatures/${literatureId}/translate-pdf/${taskId}`
  )
}

export function cancelPdfTranslate(literatureId: string, taskId: string) {
  return apiClient.post<{ code: number; msg: string }>(
    `/literatures/${literatureId}/translate-pdf/${taskId}/cancel`
  )
}

