import uuid
from datetime import datetime, timedelta

from sqlalchemy import Column, String, DateTime, Text, BigInteger, ForeignKey
from app.db.database import AlibabaBase


class ExportRecord(AlibabaBase):
    """导出记录 - 跟踪所有导出操作"""
    __tablename__ = "export_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    source_type = Column(String, nullable=False)
    source_id = Column(String, nullable=False)
    format = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    file_path = Column(Text, nullable=False)
    file_size = Column(BigInteger, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    def __repr__(self):
        return f"<ExportRecord {self.id} {self.format} {self.filename}>"

    @staticmethod
    def default_expiry() -> datetime:
        """导出文件 30 分钟后过期"""
        return datetime.utcnow() + timedelta(minutes=30)
