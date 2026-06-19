import apiClient from './client'

export interface ReadingStats {
  total_literatures: number
  read_count: number
  reading_count: number
  unread_count: number
  read_progress: number
  week_count: number
  month_count: number
  week_reading_time_seconds: number
  avg_daily_time_seconds: number
}

export interface CalendarDay {
  date: string
  pages_read: number
  time_seconds: number
}

export interface CalendarData {
  days: CalendarDay[]
}

export function getReadingStats() {
  return apiClient.get<ReadingStats>('/stats/reading')
}

export function getCalendar(days: number = 30) {
  return apiClient.get<CalendarData>('/stats/calendar', {
    params: { days },
  })
}

export function recordReading(literatureId: string, currentPage: number, durationSeconds: number = 0) {
  return apiClient.post('/stats/reading/record', {
    literature_id: literatureId,
    current_page: currentPage,
    duration_seconds: durationSeconds,
  })
}