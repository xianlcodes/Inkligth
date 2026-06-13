import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import TencentBase


class Folder(TencentBase):
    __tablename__ = "folders"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    # user_id 无 FK 约束（跨库引用 users.id）
    user_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    parent_id = Column(String, ForeignKey("folders.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    literatures = relationship("Literature", back_populates="folder", foreign_keys="Literature.folder_id")
