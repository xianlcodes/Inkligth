import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer, LargeBinary, BigInteger
from sqlalchemy.orm import relationship
from app.db.database import TencentBase
from app.models.tag import literature_tags


class Literature(TencentBase):
    __tablename__ = "literatures"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    # user_id 无 FK 约束（跨库引用 users.id）
    user_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=True)
    authors = Column(String, nullable=True)
    abstract = Column(Text, nullable=True)
    year = Column(String, nullable=True)
    journal = Column(String, nullable=True)
    doi = Column(String, nullable=True, index=True)
    file_path = Column(String, nullable=False)
    raw_text = Column(Text, nullable=True)
    translated_text = Column(LargeBinary, nullable=True)
    translated_at = Column(DateTime, nullable=True)
    status = Column(String, default="unread")
    folder_id = Column(String, ForeignKey("folders.id", ondelete="SET NULL"), nullable=True, index=True)
    total_pages = Column(Integer, nullable=True)
    last_read_page = Column(Integer, nullable=True)
    total_reading_time_seconds = Column(Integer, default=0)
    file_size = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tags = relationship("Tag", secondary=literature_tags, back_populates="literatures")
    folder = relationship("Folder", back_populates="literatures", foreign_keys=[folder_id])
