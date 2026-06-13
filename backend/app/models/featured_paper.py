import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Date, DateTime
from app.db.database import TencentBase


class FeaturedPaper(TencentBase):
    __tablename__ = "featured_papers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    arxiv_id = Column(String, unique=True, nullable=False, index=True)
    title = Column(String, nullable=False)
    authors = Column(Text, nullable=False)
    abstract = Column(Text, nullable=False)
    arxiv_url = Column(String, nullable=False)
    published_date = Column(Date, nullable=False)
    category = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
