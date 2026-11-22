import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from app.db.database import AlibabaBase


class RecallEmailLog(AlibabaBase):
    """召回邮件发送记录：每个用户每种召回类型最多发一次，防止骚扰。"""
    __tablename__ = "recall_email_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    # "no_upload_3d"（注册3天未上传）| "inactive_30d"（30天未登录）
    recall_type = Column(String, nullable=False, index=True)
    sent_at = Column(DateTime, default=datetime.utcnow)
