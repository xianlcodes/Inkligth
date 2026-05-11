import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
from app.db.database import Base


class Note(Base):
    __tablename__ = "notes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    literature_id = Column(String, ForeignKey("literatures.id", ondelete="CASCADE"), nullable=False, index=True)
    page_number = Column(String, nullable=False)
    rect_coords = Column(JSON, nullable=False)
    quoted_text = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    note_type = Column(String, default="general")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="notes")
    literature = relationship("Literature", backref="notes")