from typing import Optional

from pydantic import BaseModel


class PdfTranslateDownloadResponse(BaseModel):
    task_id: str
    status: str
    message: str


class PdfTranslateTaskStatus(BaseModel):
    task_id: str
    status: str
    progress: int = 0
    message: str = ""
    download_url: Optional[str] = None
    preview_url: Optional[str] = None
    expires_at: Optional[str] = None