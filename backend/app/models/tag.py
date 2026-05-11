import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Table, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base

literature_tags = Table(
    "literature_tags",
    Base.metadata,
    Column("literature_id", String, ForeignKey("literatures.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", String, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tags"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="tags")
    literatures = relationship("Literature", secondary=literature_tags, back_populates="tags")