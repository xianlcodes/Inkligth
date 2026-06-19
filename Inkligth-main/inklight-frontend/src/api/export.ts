/**
 * 导出系统 API 客户端
 *
 * 提供 Word / LaTeX / PDF 导出功能的前端接口。
 */

import apiClient from './client'

export interface WordExportOptions {
  include_toc?: boolean
  page_numbers?: boolean
}

export interface LatexExportOptions {
  template?: 'ieee' | 'acm' | 'neurips' | 'lncs' | 'generic'
  authors?: string[]
  abstract?: string
}

export interface FileInfo {
  name: string
  url: string
  size: number
}

export interface ExportResponse {
  export_id: string
  format: string
  filename: string
  download_url: string
  files: FileInfo[]
  compile_log: string | null
  file_size: number
  expires_at: string
}

export interface ExportHistoryItem {
  export_id: string
  format: string
  filename: string
  source_type: string
  file_size: number
  created_at: string
  download_url: string
}

export interface ExportHistoryResponse {
  items: ExportHistoryItem[]
  total: number
  page: number
  page_size: number
}

/**
 * 导出为 Word (.docx)
 */
export async function exportWord(params: {
  source_type: 'note' | 'translation' | 'literature'
  source_ids: string[]
  title?: string
  options?: WordExportOptions
}): Promise<ExportResponse> {
  const res = await apiClient.post('/export/word', params)
  return res.data
}

/**
 * 导出为 LaTeX (.tex)
 */
export async function exportLatex(params: {
  source_type: 'note' | 'translation' | 'literature'
  source_ids: string[]
  title?: string
  options?: LatexExportOptions
}): Promise<ExportResponse> {
  const res = await apiClient.post('/export/latex', params)
  return res.data
}

/**
 * 导出为 PDF
 */
export async function exportPdf(params: {
  source_type: 'note' | 'translation' | 'literature'
  source_ids: string[]
  title?: string
  options?: LatexExportOptions
}): Promise<ExportResponse> {
  const res = await apiClient.post('/export/pdf', params)
  return res.data
}

/**
 * 下载导出的文件
 */
export function getExportDownloadUrl(exportId: string): string {
  return `/api/v1/export/download/${exportId}`
}

/**
 * 获取导出历史
 */
export async function getExportHistory(params?: {
  format?: string
  page?: number
  page_size?: number
}): Promise<ExportHistoryResponse> {
  const res = await apiClient.get('/export/history', { params })
  return res.data
}
