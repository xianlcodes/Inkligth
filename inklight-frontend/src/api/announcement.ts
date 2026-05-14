import apiClient from './client'

export interface Announcement {
  id: string
  title: string
  content: string
  level: 'info' | 'warning' | 'success'
  scope: 'site_wide' | 'authenticated'
  is_pinned: boolean
  is_published: boolean
  published_at: string | null
  expires_at: string | null
  created_at: string
  updated_at: string
}

export interface AnnouncementListResponse {
  items: Announcement[]
}

export interface AnnouncementCreatePayload {
  title: string
  content: string
  level?: string
  scope?: string
  is_pinned?: boolean
  published_at?: string
  expires_at?: string
}

export interface AnnouncementUpdatePayload {
  title?: string
  content?: string
  level?: string
  scope?: string
  is_pinned?: boolean
  is_published?: boolean
  published_at?: string
  expires_at?: string
}

export function getPublicAnnouncements() {
  return apiClient.get<AnnouncementListResponse>('/announcements/public')
}

export function getActiveAnnouncements() {
  return apiClient.get<AnnouncementListResponse>('/announcements/active')
}

export function getAnnouncements(skip = 0, limit = 100) {
  return apiClient.get<AnnouncementListResponse>('/announcements', {
    params: { skip, limit },
  })
}

export function getAnnouncement(id: string) {
  return apiClient.get<Announcement>(`/announcements/${id}`)
}

export function createAnnouncement(data: AnnouncementCreatePayload) {
  return apiClient.post<Announcement>('/announcements', data)
}

export function updateAnnouncement(id: string, data: AnnouncementUpdatePayload) {
  return apiClient.patch<Announcement>(`/announcements/${id}`, data)
}

export function deleteAnnouncement(id: string) {
  return apiClient.delete(`/announcements/${id}`)
}
