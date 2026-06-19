import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, DateTime, Integer, BigInteger, Date, ForeignKey
from app.db.database import AlibabaBase


class CheckIn(AlibabaBase):
    __tablename__ = "check_ins"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    check_in_date = Column(Date, nullable=False, default=date.today)
    streak_days = Column(Integer, default=1)
    reward_bytes = Column(BigInteger, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
