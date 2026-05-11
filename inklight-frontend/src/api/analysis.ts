import apiClient from './client'

export interface SummaryData {
  background: string
  method: string
  result: string
  conclusion: string
}

export interface AnalysisData {
  id: string
  user_id: string
  literature_id: string
  summary: SummaryData | null
  innovations: string[]
  methods: string | null
  created_at: string
  updated_at: string
}

export interface AnalyzeResponse {
  task_id: string
  message: string
}

export function startAnalyze(literatureId: string) {
  return apiClient.post<AnalyzeResponse>(`/literatures/${literatureId}/analyze`)
}

export function getAnalysis(literatureId: string) {
  return apiClient.get<AnalysisData>(`/literatures/${literatureId}/analysis`)
}