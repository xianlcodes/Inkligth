import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.db.database import Base
from app.models.tag import literature_tags


class Literature(Base):
    __tablename__ = "literatures"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String, nullable=True)
    authors = Column(String, nullable=True)
    abstract = Column(Text, nullable=True)
    year = Column(String, nullable=True)
    journal = Column(String, nullable=True)
    doi = Column(String, nullable=True, index=True)
    file_path = Column(String, nullable=False)
    raw_text = Column(Text, nullable=True)
    translated_text = Column(Text, nullable=True)
    status = Column(String, default="unread")  # unread, reading, read
    total_pages = Column(Integer, nullable=True)
    last_read_page = Column(Integer, nullable=True)
    total_reading_time_seconds = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", backref="literatures")
    tags = relationship("Tag", secondary=literature_tags, back_populates="literatures")
