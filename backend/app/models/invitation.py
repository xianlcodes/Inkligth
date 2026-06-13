import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from app.db.database import AlibabaBase


class Invitation(AlibabaBase):
    __tablename__ = "invitations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    inviter_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    code = Column(String, unique=True, nullable=False, index=True)
    invitee_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    invitee_email = Column(String, nullable=True)
    reward_granted = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
