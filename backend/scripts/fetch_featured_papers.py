"""
宝塔面板定时任务脚本 — 每天拉取 arXiv 最新论文

在宝塔面板中添加定时任务：
  任务类型: shell脚本
  执行周期: 每天 02:00
  脚本内容: cd /www/wwwroot/inklight/backend && /www/wwwroot/inklight/backend/venv/bin/python scripts/fetch_featured_papers.py >> /www/wwwroot/inklight/backend/logs/arxiv_fetch.log 2>&1

首次手工执行测试：
  cd /www/wwwroot/inklight/backend && /www/wwwroot/inklight/backend/venv/bin/python scripts/fetch_featured_papers.py
"""

import asyncio
import sys
import os
from datetime import datetime

# 将项目根目录加入 sys.path，确保可以 import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main():
    from app.db.database import TencentSessionLocal
    from app.services.featured_paper_service import fetch_and_store_featured_papers
    from app.core.config import settings

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 工作目录: {os.getcwd()}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] .env 文件存在: {os.path.isfile('.env')}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 数据库地址: {settings.DATABASE_URL_FINAL}")

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始拉取 arXiv 精选论文...")

    async with TencentSessionLocal() as db:
        count = await fetch_and_store_featured_papers(db)

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 完成！共存储 {count} 篇新论文")
    return count


if __name__ == "__main__":
    count = asyncio.run(main())
    sys.exit(0 if count is not None else 1)
