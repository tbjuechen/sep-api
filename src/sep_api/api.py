"""
FastAPI RESTful API
"""

import base64
from contextlib import asynccontextmanager
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from loguru import logger

from .client import SEPClient
from .models import (
    CaptchaResponse,
    CourseListResponse,
    ErrorResponse,
    LoginRequest,
    LoginResponse,
    SelectCourseRequest,
    SelectCourseResponse,
    UserInfo,
)

# 全局客户端存储（生产环境应使用 Redis 或数据库）
_sessions: dict[str, SEPClient] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("Starting SEP API Server...")
    yield
    logger.info("Shutting down SEP API Server...")
    # 清理所有会话
    for client in _sessions.values():
        await client.close()


app = FastAPI(
    title="国科大教务系统 API",
    description="国科大教务系统 API 中转站",
    version="0.1.0",
    lifespan=lifespan,
)


def get_client(session_id: str) -> SEPClient:
    """获取客户端实例"""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found, please login first")
    return _sessions[session_id]


@app.get("/")
async def root():
    """根路径"""
    return {"message": "Welcome to SEP API", "docs": "/docs"}


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy"}


@app.post("/auth/captcha", response_model=CaptchaResponse)
async def get_captcha(session_id: str):
    """获取验证码图片"""
    client = get_client(session_id)
    image_bytes = await client.get_captcha()
    image_base64 = base64.b64encode(image_bytes).decode()
    return CaptchaResponse(success=True, image_base64=image_base64)


@app.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest, session_id: str = "default"):
    """登录"""
    # 创建新会话
    client = SEPClient()
    try:
        await client.initialize()

        # 如果没有提供验证码，先获取
        if not request.captcha:
            image_bytes = await client.get_captcha()
            captcha = await client.recognize_captcha(image_bytes)
        else:
            captcha = request.captcha

        # 执行登录
        await client.login(request.username, request.password, captcha)

        # 保存会话
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


@app.get("/user/info", response_model=LoginResponse)
async def get_user_info(session_id: str = "default"):
    """获取用户信息"""
    client = get_client(session_id)
    return LoginResponse(
        success=True,
        message="Success",
        user=UserInfo(**client.user_info),
    )


@app.get("/courses", response_model=CourseListResponse)
async def get_courses(session_id: str = "default"):
    """获取课程列表"""
    client = get_client(session_id)
    await client.xkgo()
    return CourseListResponse(
        success=True,
        courses=client.courses,
        count=len(client.courses),
    )


@app.post("/courses/search", response_model=CourseListResponse)
async def search_courses(
    course_code: str,
    session_id: str = "default",
):
    """搜索课程"""
    client = get_client(session_id)
    html = await client.select_course(course_code)
    courses = client.course_parser(html)
    return CourseListResponse(
        success=True,
        courses=courses,
        count=len(courses),
    )


@app.post("/courses/select", response_model=SelectCourseResponse)
async def select_course(
    request: SelectCourseRequest,
    session_id: str = "default",
):
    """选课"""
    client = get_client(session_id)
    try:
        status, message = await client.submit_course(request.course_code)
        return SelectCourseResponse(
            success=status == "SUCCESS",
            status=status,
            message=message or "Unknown error",
        )
    except Exception as e:
        logger.error(f"Course selection failed: {e}")
        return SelectCourseResponse(
            success=False,
            status="ERROR",
            message=str(e),
        )


@app.post("/auth/logout")
async def logout(session_id: str = "default"):
    """退出登录"""
    if session_id in _sessions:
        await _sessions[session_id].close()
        del _sessions[session_id]
        return {"success": True, "message": "Logged out"}
    return {"success": False, "message": "Session not found"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)