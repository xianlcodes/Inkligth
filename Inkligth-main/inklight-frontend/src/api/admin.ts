import apiClient from './client'

export interface StatsOverview {
  total_users: number
  total_literatures: number
  total_read_literatures: number
  total_unread_literatures: number
  total_reading_literatures: number
  total_notes: number
  total_presentations: number
}

export interface TrendPoint {
  date: string
  value: number
}

export interface TimeSeriesStats {
  new_users: TrendPoint[]
  new_literatures: TrendPoint[]
  reading_activity: TrendPoint[]
}

export interface AdminUser {
  id: string
  email: string
  username: string | null
  is_admin: boolean
  literature_count: number
  created_at: string
  updated_at: string
}

export interface AdminUserListResponse {
  total: number
  items: AdminUser[]
}

export interface OperationLog {
  id: string
  user_id: string | null
  user_email: string | null
  action: string
  resource: string | null
  resource_id: string | null
  detail: string | null
  ip_address: string | null
  status: string
  created_at: string
}

export interface OperationLogListResponse {
  total: number
  items: OperationLog[]
}

export interface SystemConfigItem {
  id: string
  key: string
  value: string | null
  category: string
  config_type: string
  label: string | null
  description: string | null
  default_value: string | null
  valid_values: string | null
  example: string | null
  is_critical: boolean
  requires_restart: boolean
  scope: string
  sort_order: number
  updated_at: string
}

export interface SystemConfigListResponse {
  items: SystemConfigItem[]
}

export interface SystemConfigCreatePayload {
  key: string
  value?: string | null
  category?: string
  config_type?: string
  label?: string | null
  description?: string | null
  default_value?: string | null
  valid_values?: string | null
  example?: string | null
  is_critical?: boolean
  requires_restart?: boolean
  scope?: string
  sort_order?: number
}

export interface SystemConfigUpdatePayload {
  value?: string | null
  category?: string
  config_type?: string
  label?: string | null
  description?: string | null
  default_value?: string | null
  valid_values?: string | null
  example?: string | null
  is_critical?: boolean
  requires_restart?: boolean
  scope?: string
  sort_order?: number
}

export interface ConfigChangeLog {
  id: string
  config_key: string
  old_value: string | null
  new_value: string | null
  changed_by: string | null
  changed_at: string
}

export interface ConfigChangeLogListResponse {
  items: ConfigChangeLog[]
}

export function getStatsOverview() {
  return apiClient.get<StatsOverview>('/admin/stats/overview')
}

export function getStatsTimeseries(period: string) {
  return apiClient.get<TimeSeriesStats>('/admin/stats/timeseries', { params: { period } })
}

export function getAdminUsers(params?: { skip?: number; limit?: number; search?: string }) {
  return apiClient.get<AdminUserListResponse>('/admin/users', { params })
}

export function updateAdminUser(userId: string, data: { is_admin?: boolean; password?: string }) {
  return apiClient.patch(`/admin/users/${userId}`, data)
}

export function getOperationLogs(params?: { skip?: number; limit?: number; user_id?: string; action?: string }) {
  return apiClient.get<OperationLogListResponse>('/admin/logs', { params })
}

export function getSystemConfigs() {
  return apiClient.get<SystemConfigListResponse>('/admin/config')
}

export function createSystemConfig(data: SystemConfigCreatePayload) {
  return apiClient.post<SystemConfigItem>('/admin/config', data)
}

export function updateSystemConfig(key: string, data: SystemConfigUpdatePayload) {
  return apiClient.put<SystemConfigItem>(`/admin/config/${encodeURIComponent(key)}`, data)
}

export function deleteSystemConfig(key: string) {
  return apiClient.delete(`/admin/config/${encodeURIComponent(key)}`)
}

export function getConfigChangeHistory(key: string) {
  return apiClient.get<ConfigChangeLogListResponse>(`/admin/config/${encodeURIComponent(key)}/history`)
}
