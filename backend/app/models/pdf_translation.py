import uuid
from datetime import datetime, timedelta
from sqlalchemy import Column, String, DateTime, BigInteger, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.db.database import TencentBase


class PdfTranslation(TencentBase):
    """原位 PDF 翻译记录，文件保留 3 天后自动清理"""
    __tablename__ = "pdf_translations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    literature_id = Column(String, ForeignKey("literatures.id", ondelete="CASCADE"), nullable=False, index=True)
    # user_id 无 FK 约束（跨库引用 users.id）
    user_id = Column(String, nullable=False, index=True)
    task_id = Column(String, nullable=False)
    source_lang = Column(String, default="en")
    target_lang = Column(String, default="zh")
    output_mode = Column(String, default="mono")
    file_path = Column(String, nullable=False)
    file_size = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    literature = relationship("Literature", backref="pdf_translations")

    __table_args__ = (
        Index("ix_pdf_translations_literature_user", "literature_id", "user_id"),
    )

    @staticmethod
    def compute_expiry() -> datetime:
        """计算过期时间：当前 UTC + 3 天（DB 存储为 naive UTC）"""
        return datetime.utcnow() + timedelta(days=3)
