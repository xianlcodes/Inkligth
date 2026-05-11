import apiClient from './client'

export interface SearchResultItem {
  id: string
  literature_id: string
  chunk_index: number
  chunk_text: string
  page_number: number | null
  literature_title: string
  similarity: number
}

export interface SearchResponse {
  query: string
  total: number
  items: SearchResultItem[]
}

export function searchLiterature(q: string, topN: number = 10) {
  return apiClient.get<SearchResponse>('/search', {
    params: { q, top_n: topN },
  })
}