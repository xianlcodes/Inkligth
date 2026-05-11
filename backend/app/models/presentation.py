import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from app.db.database import Base


class Presentation(Base):
    __tablename__ = "presentations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    literature_id = Column(String, ForeignKey("literatures.id", ondelete="SET NULL"), nullable=True, index=True)
    literature_title = Column(String(500), nullable=True)
    slides = Column(JSON, nullable=False, default=list)
    slide_count = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", backref="presentations")
    literature = relationship("Literature", backref="presentations")