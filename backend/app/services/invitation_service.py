import logging
import secrets
import string
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.invitation import Invitation
from app.models.user import User
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

INVITER_REWARD = 50 * 1024 * 1024
INVITEE_REWARD = 20 * 1024 * 1024
MAX_ACTIVE_CODES = 5


def _generate_code() -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(8))


class InvitationService:
    @staticmethod
    async def generate_code(db: AsyncSession, user_id: str) -> str:
        active_count = await db.execute(
            select(func.count(Invitation.id)).where(
                Invitation.inviter_id == user_id,
                Invitation.is_active == True,
            )
        )
        if active_count.scalar() >= MAX_ACTIVE_CODES:
            raise ValueError(f"最多同时持有 {MAX_ACTIVE_CODES} 个有效邀请码")

        for _ in range(10):
            code = _generate_code()
            existing = await db.execute(select(Invitation).where(Invitation.code == code))
            if not existing.scalar_one_or_none():
                break
        else:
            raise RuntimeError("无法生成唯一邀请码")

        invitation = Invitation(inviter_id=user_id, code=code)
        db.add(invitation)
        await db.commit()
        await db.refresh(invitation)
        return code

    @staticmethod
    async def get_invitations(db: AsyncSession, user_id: str) -> dict:
        codes_result = await db.execute(
            select(Invitation).where(
                Invitation.inviter_id == user_id,
                Invitation.is_active == True,
            ).order_by(Invitation.created_at.desc())
        )
        codes = codes_result.scalars().all()

        invited_result = await db.execute(
            select(Invitation).where(
                Invitation.inviter_id == user_id,
                Invitation.invitee_id.isnot(None),
            ).order_by(Invitation.created_at.desc())
        )
        invited = invited_result.scalars().all()

        invited_users = []
        for inv in invited:
            invited_users.append({
                "email": inv.invitee_email or "",
                "registered_at": inv.created_at,
                "reward_granted": inv.reward_granted,
            })

        return {
            "codes": [
                {"code": c.code, "is_active": c.is_active, "created_at": c.created_at}
                for c in codes
            ],
            "invited_users": invited_users,
        }

    @staticmethod
    async def process_invitation(db: AsyncSession, invite_code: str, invitee_id: str, invitee_email: str):
        result = await db.execute(
            select(Invitation).where(
                Invitation.code == invite_code,
                Invitation.is_active == True,
            )
        )
        invitation = result.scalar_one_or_none()
        if not invitation:
            return

        invitation.invitee_id = invitee_id
        invitation.invitee_email = invitee_email
        invitation.reward_granted = True
        invitation.is_active = False

        await StorageService.add_bonus_space(db, invitation.inviter_id, "invitation", INVITER_REWARD)
        await StorageService.add_bonus_space(db, invitee_id, "invitation", INVITEE_REWARD)

        await db.commit()
        logger.info(f"Invitation processed: {invite_code} -> inviter={invitation.inviter_id}, invitee={invitee_id}")

    @staticmethod
    async def ensure_user_invite_code(db: AsyncSession, user: User) -> str:
        if user.invite_code:
            return user.invite_code
        for _ in range(10):
            code = _generate_code()
            existing = await db.execute(select(User).where(User.invite_code == code))
            if not existing.scalar_one_or_none():
                user.invite_code = code
                await db.commit()
                return code
        raise RuntimeError("无法生成唯一邀请码")