import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean
from app.db.database import Base


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, index=True, nullable=False)
    token = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
