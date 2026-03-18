"""
认证相关端点
"""

import base64

from fastapi import APIRouter
from loguru import logger

from ..client import SEPClient
from ..deps import _sessions, get_client
from ..models import CaptchaResponse, LoginRequest, LoginResponse, UserInfo

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/captcha", response_model=CaptchaResponse)
async def get_captcha(session_id: str):
    """获取验证码图片"""
    client = get_client(session_id)
    image_bytes = await client.get_captcha()
    image_base64 = base64.b64encode(image_bytes).decode()
    return CaptchaResponse(success=True, image_base64=image_base64)


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, session_id: str = "default"):
    """登录"""
    client = SEPClient()
    try:
        await client.initialize()

        if not request.captcha:
            image_bytes = await client.get_captcha()
            captcha = await client.recognize_captcha(image_bytes)
        else:
            captcha = request.captcha

        await client.login(request.username, request.password, captcha)

        _sessions[session_id] = client

        return LoginResponse(
            success=True,
            message="Login successful",
            user=UserInfo(**client.user_info),
        )
    except Exception as e:
        await client.close()
        logger.error(f"Login failed: {e}")
        return LoginResponse(success=False, message=str(e))


@router.post("/logout")
async def logout(session_id: str = "default"):
    """退出登录"""
    if session_id in _sessions:
        await _sessions[session_id].close()
        del _sessions[session_id]
        return {"success": True, "message": "Logged out"}
    return {"success": False, "message": "Session not found"}
