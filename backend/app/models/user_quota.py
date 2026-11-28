import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime
from app.db.database import AlibabaBase


class UserQuota(AlibabaBase):
    """用户平台免费额度。

    设计要点：
    - 平台免费额度仅用于 PDF 文献翻译任务（1 次 = 1 次），由
      QuotaService 原子扣减/返还，避免并发超发；
    - 每日额度模式（platform_free_translations > 0）：每人每天 N 次，
      按北京时间日界跨天懒重置（daily_date != 今天 即视为新一天）；
    - daily_used 超出当日次数后，回退消耗 free_translations 余额
      （签到里程碑等运营场景赠送的额度）；
    - 不限量模式（platform_free_translations = -1）：不扣减任何余额，
      仅记录 used_count 供运营统计；
    - 用户自配 AI 引擎时不消耗平台额度（无限量）；
    - 记录按 user_id 懒创建，存量用户同样覆盖；
    - prefer_free：翻译通道偏好。True = 优先使用平台免费额度
      （自有 Key 用户也可选，用完自动回退自有 Key）；False = 优先自有 Key。
    """
    __tablename__ = "user_quotas"

    user_id = Column(String, primary_key=True)
    # 赠送余额（签到里程碑等运营场景发放）；每日额度用完后兜底消耗
    free_translations = Column(Integer, nullable=False, default=0)
    # 累计消耗次数（统计口径；不限量模式下也记账）
    used_count = Column(Integer, nullable=False, default=0)
    # 当日已消耗次数（每日额度模式）
    daily_used = Column(Integer, nullable=False, default=0)
    # 当日计数所属的北京时间日期（YYYY-MM-DD）；与当天不同即触发懒重置
    daily_date = Column(String(10), nullable=True)
    # 翻译通道偏好（见类文档）
    prefer_free = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
