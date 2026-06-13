import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, BigInteger, ForeignKey
from app.db.database import AlibabaBase


class UserStorage(AlibabaBase):
    __tablename__ = "user_storages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    total_space = Column(BigInteger, default=209715200)
    used_space = Column(BigInteger, default=0)
    base_space = Column(BigInteger, default=209715200)
    check_in_bonus = Column(BigInteger, default=0)
    invitation_bonus = Column(BigInteger, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
