import apiClient from './client'

export interface CheckInStatus {
  checked_in_today: boolean
  streak_days: number
  today_reward: number
  checked_dates: string[]
}

export interface CheckInResult {
  streak_days: number
  reward_bytes: number
  total_check_in_bonus: number
}

export async function doCheckIn(): Promise<CheckInResult> {
  const res = await apiClient.post('/check-in')
  return res.data
}

export async function getCheckInStatus(): Promise<CheckInStatus> {
  const res = await apiClient.get('/check-in/status')
  return res.data
}