import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Text, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import AlibabaBase


class Tutorial(AlibabaBase):
    __tablename__ = "tutorials"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False, default="")
    summary = Column(String(500), nullable=True)
    is_published = Column(Boolean, default=False)
    published_at = Column(DateTime, nullable=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    versions = relationship("TutorialVersion", back_populates="tutorial",
                            order_by="TutorialVersion.version_number.desc()",
                            lazy="selectin")


class TutorialVersion(AlibabaBase):
    __tablename__ = "tutorial_versions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tutorial_id = Column(String, ForeignKey("tutorials.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False, default="")
    summary = Column(String(500), nullable=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    tutorial = relationship("Tutorial", back_populates="versions")
