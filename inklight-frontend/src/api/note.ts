import apiClient from './client'

export interface RectCoords {
  x: number
  y: number
  width: number
  height: number
}

export interface Note {
  id: string
  user_id: string
  literature_id: string
  literature_title?: string | null
  page_number: string
  rect_coords: RectCoords
  quoted_text: string | null
  content: string | null
  note_type: 'general' | 'innovation' | 'method' | 'question'
  created_at: string
}

export interface NoteCreatePayload {
  literature_id: string
  page_number: string
  rect_coords: RectCoords
  quoted_text?: string
  content?: string
  note_type?: string
}

export interface NoteUpdatePayload {
  content?: string
  note_type?: string
}

export interface NoteListResponse {
  total: number
  items: Note[]
}

export function createNote(data: NoteCreatePayload) {
  return apiClient.post<Note>('/notes', data)
}

export function getNotes(literatureId?: string, noteType?: string) {
  const params: Record<string, string> = {}
  if (literatureId) params.literature_id = literatureId
  if (noteType) params.note_type = noteType
  return apiClient.get<NoteListResponse>('/notes', { params })
}

export function getNote(noteId: string) {
  return apiClient.get<Note>(`/notes/${noteId}`)
}

export function updateNote(noteId: string, data: NoteUpdatePayload) {
  return apiClient.patch<Note>(`/notes/${noteId}`, data)
}

export function deleteNote(noteId: string) {
  return apiClient.delete(`/notes/${noteId}`)
}