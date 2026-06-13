import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Integer, Boolean, ForeignKey
from app.db.database import AlibabaBase


class OperationLog(AlibabaBase):
    __tablename__ = "operation_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    user_email = Column(String, nullable=True)
    action = Column(String, nullable=False, index=True)
    resource = Column(String, nullable=True)
    resource_id = Column(String, nullable=True)
    detail = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    status = Column(String, default="success")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class SystemConfig(AlibabaBase):
    __tablename__ = "system_configs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    key = Column(String, unique=True, index=True, nullable=False)
    value = Column(Text, nullable=True)
    category = Column(String, default="general", index=True)
    config_type = Column(String, default="text")
    label = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    default_value = Column(String, nullable=True)
    valid_values = Column(Text, nullable=True)
    example = Column(String, nullable=True)
    is_critical = Column(Boolean, default=False)
    requires_restart = Column(Boolean, default=False)
    scope = Column(String, default="admin")
    sort_order = Column(Integer, default=0)
    updated_by = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class ConfigChangeLog(AlibabaBase):
    __tablename__ = "config_change_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    config_key = Column(String, ForeignKey("system_configs.key", ondelete="CASCADE"), nullable=False, index=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    changed_by = Column(String, nullable=True)
    changed_at = Column(DateTime, default=datetime.utcnow, index=True)
