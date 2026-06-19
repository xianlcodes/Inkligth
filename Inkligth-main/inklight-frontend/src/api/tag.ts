import apiClient from './client'

export interface TagItem {
  id: string
  user_id: string
  name: string
  created_at: string
}

export interface TagCloudItem {
  name: string
  count: number
}

export interface TagCloudResponse {
  tags: TagCloudItem[]
}

export interface LiteratureTagsResponse {
  literature_id: string
  tags: TagItem[]
}

export function addTagToLiterature(literatureId: string, tagName: string) {
  return apiClient.post<TagItem>(`/literatures/${literatureId}/tags`, null, {
    params: { tag_name: tagName },
  })
}

export function removeTagFromLiterature(literatureId: string, tagId: string) {
  return apiClient.delete(`/literatures/${literatureId}/tags/${tagId}`)
}

export function getLiteratureTags(literatureId: string) {
  return apiClient.get<LiteratureTagsResponse>(`/literatures/${literatureId}/tags`)
}

export function getTagCloud() {
  return apiClient.get<TagCloudResponse>('/tags/cloud')
}