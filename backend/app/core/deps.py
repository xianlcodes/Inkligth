from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.db.database import AlibabaSessionLocal
from app.core.security import decode_token
from app.services.user_service import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
) -> dict:
    """解析 Bearer token 并返回当前用户。

    关键：这里必须用「短会话」——取完用户立即归还连接，而不是声明
    Depends(get_user_db)。yield 型依赖的会话会被 FastAPI 保持到「响应结束」，
    而 SSE 流式接口（翻译/边看边问等）的响应会持续数十秒到数分钟，
    每个并发流式用户都会占住一个用户库连接，把连接池打满，
    导致全站 500（QueuePool limit ... connection timed out，2026-11-20 事故）。
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user_id = decode_token(token)
    if user_id is None:
        raise credentials_exception
    async with AlibabaSessionLocal() as db:
        user = await UserService.get_user_by_id(db, user_id)
    if user is None:
        raise credentials_exception
    return user
