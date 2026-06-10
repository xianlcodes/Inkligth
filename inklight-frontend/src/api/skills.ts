/**
 * Skills/Hooks 系统 API 客户端
 */

import apiClient from './client'

// ── Types ──

export interface Skill {
  id: string
  name: string
  description: string
  layer: 'soul' | 'agents' | 'identity'
  content: string
  is_active: boolean
  match_topic: string | null
  category: string
  priority: number
  created_at: string
  updated_at: string
}

export interface SkillListResponse {
  total: number
  items: Skill[]
}

export interface SkillCreateParams {
  name: string
  description: string
  layer: 'soul' | 'agents' | 'identity'
  content: string
  is_active?: boolean
  match_topic?: string | null
  category?: string
  priority?: number
}

export interface SkillUpdateParams {
  description?: string
  layer?: 'soul' | 'agents' | 'identity'
  content?: string
  is_active?: boolean
  match_topic?: string | null
  category?: string
  priority?: number
}

export interface Hook {
  id: string
  name: string
  description: string
  hook_point: 'pre_tool_use' | 'post_tool_use' | 'on_error'
  action_type: 'log' | 'throttle' | 'filter' | 'custom'
  config: Record<string, unknown> | null
  priority: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface HookListResponse {
  total: number
  items: Hook[]
}

export interface HookCreateParams {
  name: string
  description: string
  hook_point: 'pre_tool_use' | 'post_tool_use' | 'on_error'
  action_type: 'log' | 'throttle' | 'filter' | 'custom'
  config?: Record<string, unknown>
  priority?: number
  is_active?: boolean
}

export interface SkillChatParams {
  message: string
  context_text?: string
  conversation_id?: string
}

export interface SkillChatResponse {
  reply: string
  conversation_id: string
  title: string
}

export interface SkillPreset {
  name: string
  label_cn: string
  description: string
  desc_cn: string
  layer: string
  match_topic: string | null
  category: string
}

// ── Skills ──

export async function getSkills(params?: {
  layer?: string
  topic?: string
  category?: string
  skip?: number
  limit?: number
}): Promise<SkillListResponse> {
  const res = await apiClient.get('/skills', { params })
  return res.data
}

export async function createSkill(data: SkillCreateParams): Promise<Skill> {
  const res = await apiClient.post('/skills', data)
  return res.data
}

export async function getSkill(id: string): Promise<Skill> {
  const res = await apiClient.get(`/skills/${id}`)
  return res.data
}

export async function updateSkill(id: string, data: SkillUpdateParams): Promise<Skill> {
  const res = await apiClient.put(`/skills/${id}`, data)
  return res.data
}

export async function deleteSkill(id: string): Promise<void> {
  await apiClient.delete(`/skills/${id}`)
}

export async function toggleSkill(id: string): Promise<Skill> {
  const res = await apiClient.post(`/skills/${id}/toggle`)
  return res.data
}

// ── Presets ──

export async function getSkillPresets(): Promise<{ presets: SkillPreset[] }> {
  const res = await apiClient.get('/skills/presets/list')
  return res.data
}

export async function installPresetSkill(presetName: string): Promise<Skill> {
  const res = await apiClient.post(`/skills/presets/install?preset_name=${presetName}`)
  return res.data
}

export async function installAllPresets(): Promise<{ installed: number; message: string }> {
  const res = await apiClient.post('/skills/presets/install-all')
  return res.data
}

// ── Hooks ──

export async function getHooks(params?: {
  hook_point?: string
  skip?: number
  limit?: number
}): Promise<HookListResponse> {
  const res = await apiClient.get('/hooks', { params })
  return res.data
}

export async function createHook(data: HookCreateParams): Promise<Hook> {
  const res = await apiClient.post('/hooks', data)
  return res.data
}

export async function getHook(id: string): Promise<Hook> {
  const res = await apiClient.get(`/hooks/${id}`)
  return res.data
}

export async function updateHook(id: string, data: Partial<HookCreateParams>): Promise<Hook> {
  const res = await apiClient.put(`/hooks/${id}`, data)
  return res.data
}

export async function deleteHook(id: string): Promise<void> {
  await apiClient.delete(`/hooks/${id}`)
}

export async function toggleHook(id: string): Promise<Hook> {
  const res = await apiClient.post(`/hooks/${id}/toggle`)
  return res.data
}

// ── Chat with Skills ──

export async function chatWithPaper(
  literatureId: string,
  params: SkillChatParams,
): Promise<SkillChatResponse> {
  const res = await apiClient.post(`/papers/${literatureId}/chat`, params)
  return res.data
}
