"""
导出服务层 - 管理导出操作的生命周期
"""

import uuid
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.export.models import ExportRecord
from app.export.word_exporter import markdown_to_docx

logger = logging.getLogger(__name__)

# 导出文件存储根目录
# 相对于应用根目录（backend/）
EXPORT_DIR = Path(__file__).resolve().parent.parent.parent / "export_files"

# 文件最大 50MB
MAX_FILE_SIZE = 50 * 1024 * 1024

# 过期时间 30 分钟
EXPORT_TTL_MINUTES = 30


def _get_export_dir(user_id: str) -> Path:
    """获取用户导出目录"""
    user_dir = EXPORT_DIR / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def _ensure_export_dir():
    """确保导出根目录存在"""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)


class ExportService:
    """导出服务 - 调度导出、文件管理、过期清理"""

    @staticmethod
    async def _get_source_content(db: AsyncSession, user_id: str, source_type: str, source_ids: list[str]) -> tuple[str, str]:
        """
        根据来源类型从数据库获取真实内容与标题。

        - literature  : 从 literatures.raw_text 取原文
        - translation : 从 translations.content 取最新译文
        - note        : 从 notes 表取所有笔记
        """
        if not source_ids:
            return "# （无内容）\n\n未指定导出来源。", "空导出"

        lid = source_ids[0]  # 目前只支持单篇文献导出

        if source_type == "literature":
            from app.models.literature import Literature
            from sqlalchemy import select
            result = await db.execute(select(Literature).where(Literature.id == lid))
            lit = result.scalar_one_or_none()
            if not lit:
                return "# （文献不存在）\n\n未找到对应的文献记录。", "文献不存在"

            parts = [f"# {lit.title or 'Untitled'}"]
            if lit.authors:
                parts.append(f"**作者：** {lit.authors}")
            if lit.year:
                parts.append(f"**年份：** {lit.year}")
            if lit.abstract:
                parts.append(f"## 摘要\n\n{lit.abstract}")
            if lit.raw_text:
                parts.append(f"## 正文\n\n{lit.raw_text}")
            else:
                parts.append("\n*（文献正文尚未解析，无法导出全文）*")

            markdown_content = "\n\n".join(parts)
            title = lit.title or "Literature Export"
            return markdown_content, title

        elif source_type == "translation":
            from app.models.translation import Translation
            from sqlalchemy import select
            result = await db.execute(
                select(Translation)
                .where(
                    Translation.literature_id == lid,
                    Translation.user_id == user_id,
                )
                .order_by(Translation.created_at.desc())
                .limit(1)
            )
            trans = result.scalar_one_or_none()
            if not trans or not trans.content:
                return "# （无译文）\n\n未找到该文献的 AI 翻译结果。", "无译文"

            decoded = trans.content.decode("utf-8", errors="replace")
            markdown_content = f"# AI 翻译结果\n\n{decoded}"
            title = "Translation Export"
            return markdown_content, title

        elif source_type == "note":
            from app.models.note import Note
            from sqlalchemy import select
            result = await db.execute(
                select(Note)
                .where(
                    Note.literature_id == lid,
                    Note.user_id == user_id,
                )
                .order_by(Note.page_number.asc(), Note.created_at.asc())
            )
            notes = list(result.scalars().all())
            if not notes:
                return "# （无笔记）\n\n该文献下暂无笔记。", "无笔记"

            items = []
            for n in notes:
                item = f"### 笔记（第 {n.page_number} 页）"
                if n.quoted_text:
                    item += f"\n\n> {n.quoted_text}"
                if n.content:
                    item += f"\n\n{n.content}"
                items.append(item)

            md = f"# 论文笔记\n\n共 {len(notes)} 条笔记\n\n"
            md += "\n\n---\n\n".join(items)
            return md, "Notes Export"

        else:
            return f"# 不支持的来源类型: {source_type}", "Unknown"



    @staticmethod
    async def create_word_export(
        db: AsyncSession,
        user_id: str,
        source_type: str,
        source_ids: list[str],
        title: str = "InkLight Export",
        include_toc: bool = False,
        page_numbers: bool = True,
    ) -> ExportRecord:
        """创建 Word 导出"""
        _ensure_export_dir()

        # 获取内容
        content, content_title = await ExportService._get_source_content(db, user_id, source_type, source_ids)
        if title == "InkLight Export":
            title = content_title

        # 生成文件名
        safe_title = "".join(c for c in title if c.isalnum() or c in " _-").strip() or "export"
        filename = f"{safe_title}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.docx"
        user_dir = _get_export_dir(user_id)
        output_path = str(user_dir / filename)

        # 执行转换
        try:
            markdown_to_docx(
                content,
                output_path,
                title=title,
                include_toc=include_toc,
                page_numbers=page_numbers,
            )
        except Exception:
            logger.exception("Word export failed for user %s", user_id)
            raise

        # 检查文件大小
        file_size = os.path.getsize(output_path)
        if file_size > MAX_FILE_SIZE:
            os.remove(output_path)
            raise ValueError(f"Export file exceeds maximum size of {MAX_FILE_SIZE} bytes")

        # 保存记录
        record = ExportRecord(
            user_id=user_id,
            source_type=source_type,
            source_id=",".join(source_ids[:10]),  # 最多存10个ID
            format="word",
            filename=filename,
            file_path=output_path,
            file_size=file_size,
            expires_at=datetime.utcnow() + timedelta(minutes=EXPORT_TTL_MINUTES),
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        logger.info("Word export created: %s for user %s", record.id, user_id)
        return record

    @staticmethod
    async def create_latex_export(
        db: AsyncSession,
        user_id: str,
        source_type: str,
        source_ids: list[str],
        title: str = "InkLight Export",
        template: str = "generic",
        authors: list[str] = None,
        abstract: str = "",
    ) -> ExportRecord:
        """创建 LaTeX 导出"""
        _ensure_export_dir()
        authors = authors or []

        content, content_title = await ExportService._get_source_content(db, user_id, source_type, source_ids)
        if title == "InkLight Export":
            title = content_title

        safe_title = "".join(c for c in title if c.isalnum() or c in " _-").strip() or "export"
        filename = f"{safe_title}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.tex"
        user_dir = _get_export_dir(user_id)
        output_path = str(user_dir / filename)

        from app.export.latex_exporter import markdown_to_latex
        try:
            markdown_to_latex(
                content,
                output_path,
                template=template,
                title=title,
                authors=authors,
                abstract=abstract,
            )
        except NotImplementedError:
            raise
        except Exception:
            logger.exception("LaTeX export failed for user %s", user_id)
            raise

        file_size = os.path.getsize(output_path)
        if file_size > MAX_FILE_SIZE:
            os.remove(output_path)
            raise ValueError(f"Export file exceeds maximum size of {MAX_FILE_SIZE} bytes")

        record = ExportRecord(
            user_id=user_id,
            source_type=source_type,
            source_id=",".join(source_ids[:10]),
            format="latex",
            filename=filename,
            file_path=output_path,
            file_size=file_size,
            expires_at=datetime.utcnow() + timedelta(minutes=EXPORT_TTL_MINUTES),
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        logger.info("LaTeX export created: %s for user %s", record.id, user_id)
        return record

    @staticmethod
    async def create_pdf_export(
        db: AsyncSession,
        user_id: str,
        source_type: str,
        source_ids: list[str],
        title: str = "InkLight Export",
        template: str = "generic",
        authors: list[str] = None,
        abstract: str = "",
    ) -> ExportRecord:
        """创建 PDF 导出（Markdown → LaTeX → PDF）"""
        _ensure_export_dir()
        authors = authors or []

        content, content_title = await ExportService._get_source_content(db, user_id, source_type, source_ids)
        if title == "InkLight Export":
            title = content_title

        safe_title = "".join(c for c in title if c.isalnum() or c in " _-").strip() or "export"
        filename = f"{safe_title}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
        user_dir = _get_export_dir(user_id)
        output_path = str(user_dir / filename)

        from app.export.latex_exporter import markdown_to_pdf
        try:
            success, pdf_path, compile_log = markdown_to_pdf(
                content,
                output_path,
                template=template,
                title=title,
                authors=authors,
                abstract=abstract,
            )
        except NotImplementedError:
            raise
        except Exception:
            logger.exception("PDF export failed for user %s", user_id)
            raise

        if not success:
            raise RuntimeError(f"PDF compilation failed:\n{compile_log[:1000]}")

        file_size = os.path.getsize(output_path)
        if file_size > MAX_FILE_SIZE:
            os.remove(output_path)
            raise ValueError(f"Export file exceeds maximum size of {MAX_FILE_SIZE} bytes")

        record = ExportRecord(
            user_id=user_id,
            source_type=source_type,
            source_id=",".join(source_ids[:10]),
            format="pdf",
            filename=filename,
            file_path=output_path,
            file_size=file_size,
            expires_at=datetime.utcnow() + timedelta(minutes=EXPORT_TTL_MINUTES),
        )
        record._compile_log = compile_log if not success else None
        db.add(record)
        await db.commit()
        await db.refresh(record)
        logger.info("PDF export created: %s for user %s", record.id, user_id)
        return record

    @staticmethod
    async def get_export_record(db: AsyncSession, export_id: str) -> Optional[ExportRecord]:
        """获取导出记录"""
        result = await db.execute(select(ExportRecord).where(ExportRecord.id == export_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_export(
        db: AsyncSession, user_id: str, export_id: str
    ) -> Optional[ExportRecord]:
        """获取用户的导出记录（含用户权限校验）"""
        result = await db.execute(
            select(ExportRecord).where(
                ExportRecord.id == export_id,
                ExportRecord.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_export_history(
        db: AsyncSession,
        user_id: str,
        fmt: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[int, list[ExportRecord]]:
        """获取导出历史"""
        conditions = [ExportRecord.user_id == user_id]
        if fmt:
            conditions.append(ExportRecord.format == fmt)

        # 总数
        count_q = select(type(ExportRecord).id).where(*conditions)
        count_result = await db.execute(count_q)
        total = len(count_result.scalars().all())

        # 分页
        q = (
            select(ExportRecord)
            .where(*conditions)
            .order_by(ExportRecord.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(q)
        items = list(result.scalars().all())
        return total, items

    @staticmethod
    async def cleanup_expired_files(db: AsyncSession) -> int:
        """清理过期的导出文件和记录"""
        now = datetime.utcnow()
        result = await db.execute(
            select(ExportRecord).where(ExportRecord.expires_at < now)
        )
        expired = list(result.scalars().all())
        count = 0
        for record in expired:
            try:
                if os.path.exists(record.file_path):
                    os.remove(record.file_path)
                    count += 1
            except OSError:
                logger.warning("Failed to remove expired export file: %s", record.file_path)
            await db.delete(record)
        await db.commit()
        if count:
            logger.info("Cleaned up %d expired export files", count)
        return count
