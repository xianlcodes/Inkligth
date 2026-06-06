import apiClient from './client'

export interface FeaturedPaper {
  id: string
  arxiv_id: string
  title: string
  authors: string
  abstract: string
  arxiv_url: string
  published_date: string
  category: string
}

export interface FeaturedPaperListResponse {
  items: FeaturedPaper[]
  total: number
}

export async function fetchFeaturedPapers(limit = 15): Promise<FeaturedPaperListResponse> {
  const res = await apiClient.get<FeaturedPaperListResponse>('/featured', {
    params: { limit },
  })
  return res.data
}
