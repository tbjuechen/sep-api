"""
用户相关端点
"""

from fastapi import APIRouter

from ..deps import get_client
from ..models import LoginResponse, UserInfo

router = APIRouter(prefix="/user", tags=["用户"])


@router.get("/info", response_model=LoginResponse)
async def get_user_info(session_id: str = "default"):
    """获取用户信息"""
    client = get_client(session_id)
    return LoginResponse(
        success=True,
        message="Success",
        user=UserInfo(**client.user_info),
    )
