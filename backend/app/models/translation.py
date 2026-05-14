import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, LargeBinary, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.db.database import Base


class Translation(Base):
    __tablename__ = "translations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    literature_id = Column(String, ForeignKey("literatures.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content_hash = Column(String(64), nullable=False)
    engine_version = Column(String, nullable=True)
    translation_style = Column(String, nullable=True)
    content = Column(LargeBinary, nullable=False)
    paragraph_count = Column(String, default="0")
    created_at = Column(DateTime, default=datetime.utcnow)

    literature = relationship("Literature", backref="translations")

    __table_args__ = (
        Index("ix_translations_literature_hash", "literature_id", "content_hash"),
    )
