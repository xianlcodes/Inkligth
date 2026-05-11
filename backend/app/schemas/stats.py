from pydantic import BaseModel
from typing import Optional
from datetime import date


class ReadingStatsResponse(BaseModel):
    total_literatures: int
    read_count: int
    reading_count: int
    unread_count: int
    read_progress: float
    week_count: int
    month_count: int
    week_reading_time_seconds: int
    avg_daily_time_seconds: int


class CalendarDay(BaseModel):
    date: date
    pages_read: int
    time_seconds: int


class CalendarResponse(BaseModel):
    days: list[CalendarDay]


class RecordReadingRequest(BaseModel):
    literature_id: str
    current_page: int
    duration_seconds: int = 0


class RecordReadingResponse(BaseModel):
    message: str