import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime
from app.db.database import AlibabaBase


class UserQuota(AlibabaBase):
    """用户平台免费额度。

    设计要点：
    - 平台免费额度仅用于 PDF 文献翻译任务（1 篇 = 1 次），由
      QuotaService 原子扣减/返还，避免并发超发；
    - 用户自配 AI 引擎时不消耗平台额度（无限量）；
    - 记录按 user_id 懒创建：新用户首次查询时自动发放
      settings.PLATFORM_FREE_TRANSLATIONS 次额度，存量用户同样覆盖；
    - prefer_free：翻译通道偏好。True = 优先使用平台免费额度
      （自有 Key 用户也可选，用完自动回退自有 Key）；False = 优先自有 Key。
    """
    __tablename__ = "user_quotas"

    user_id = Column(String, primary_key=True)
    # 剩余可用次数；consume 用 UPDATE ... WHERE free_translations > 0 保证原子性
    free_translations = Column(Integer, nullable=False, default=0)
    # 累计消耗次数（只增不减，用于统计；返还额度时不回退此值）
    used_count = Column(Integer, nullable=False, default=0)
    # 翻译通道偏好（见类文档）
    prefer_free = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
