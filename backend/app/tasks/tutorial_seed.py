"""内置教程种子：首次启动时写入「免费获取 AI Key」教程（幂等，按标题查重）。

背景：教程内容此前完全依赖管理员在后台手录，导致教程页是空壳，
新用户无法找到免费 Key 的申请方式（docs/GLM-4.7-Flash-配置指南.md
一直躺在仓库里没有入口）。这里把它作为种子教程写入，后续管理员
可在后台继续补充。
"""
import logging
from datetime import datetime

from sqlalchemy import select

from app.db.database import AlibabaSessionLocal
from app.models.user import User
from app.models.tutorial import Tutorial
from app.services.tutorial_service import TutorialService

logger = logging.getLogger(__name__)

SEED_TITLE = "免费获取 AI Key：GLM-4.7-Flash 配置指南（3 步）"

SEED_SUMMARY = "3 步免费获取并配置 GLM-4.7-Flash（完全免费的模型，无需充值），解锁无限翻译。"

SEED_CONTENT = """## 第 1 步：获取免费 API Key（约 2 分钟）

1. 访问 **智谱AI开放平台**：https://bigmodel.cn/
2. 注册 / 登录账号
3. 进入 **控制台** → **API Keys**
4. 点击 **创建新的 API Key**，复制保存

> GLM-4.7-Flash 是**完全免费**的模型，注册后即可使用，**无需充值**。

## 第 2 步：在研墨中配置（约 1 分钟）

1. 登录研墨后，点击左侧导航栏 **设置** → **AI 引擎配置**
2. 点击右上角 **添加引擎**
3. 在 **供应商** 下拉框选择 **GLM (智谱)** —— API 地址和模型会自动填好
4. 在 **API Key** 输入框粘贴你刚复制的 Key
5. 打开 **设为默认** 开关 → 点击 **保存**

## 第 3 步：测试

保存后点击 **测试连接**，看到「✅ 连接成功」即配置完成。

配置自己的 Key 后：翻译、全文翻译、划词翻译、AI 问答、组会 PPT、学术写作**全部不限量使用**。

---

*遇到问题可加入官方 QQ 群交流。*
"""


async def ensure_seed_tutorials() -> None:
    """幂等写入内置教程；无管理员账号或数据库不可用时静默跳过。"""
    title = SEED_TITLE
    try:
        async with AlibabaSessionLocal() as db:
            exists = (
                await db.execute(select(Tutorial).where(Tutorial.title == title))
            ).scalar_one_or_none()
            if exists:
                return

            admin = (
                await db.execute(
                    select(User).where(User.is_admin.is_(True)).order_by(User.created_at).limit(1)
                )
            ).scalar_one_or_none()
            if not admin:
                logger.info("教程种子跳过：数据库中尚无管理员账号")
                return

            tutorial = await TutorialService.create_tutorial(
                db,
                {"title": title, "content": SEED_CONTENT, "summary": SEED_SUMMARY},
                user_id=str(admin.id),
            )
            tutorial.is_published = True
            tutorial.published_at = datetime.utcnow()
            await db.commit()
            logger.info("内置教程已写入并发布: %s", title)
    except Exception as e:
        logger.warning("教程种子写入失败（不影响启动）: %s", e)
