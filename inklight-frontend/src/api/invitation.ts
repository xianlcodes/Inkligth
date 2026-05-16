import apiClient from './client'

export interface InvitationCode {
  code: string
  is_active: boolean
  created_at: string
}

export interface InvitedUser {
  email: string
  registered_at: string
  reward_granted: boolean
}

export interface InvitationList {
  codes: InvitationCode[]
  invited_users: InvitedUser[]
  invite_url: string
}

export interface GenerateCodeResult {
  code: string
}

export async function getInvitations(): Promise<InvitationList> {
  const res = await apiClient.get('/invitations')
  return res.data
}

export async function generateInvitationCode(): Promise<GenerateCodeResult> {
  const res = await apiClient.post('/invitations/generate')
  return res.data
}