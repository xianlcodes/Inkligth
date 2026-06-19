import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean
from app.db.database import AlibabaBase


class User(AlibabaBase):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    username = Column(String, nullable=True)
    is_admin = Column(Boolean, default=False)
    avatar_style = Column(String, nullable=True)
    agreed_terms_at = Column(DateTime, nullable=True)
    theme_color = Column(String, default="#e8f2e2")
    invite_code = Column(String, unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
