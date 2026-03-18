"""
课程相关端点
"""

from fastapi import APIRouter
from loguru import logger

from ..deps import get_client
from ..models import CourseListResponse, SelectCourseRequest, SelectCourseResponse
from ..services.xkgo import XkgoService

router = APIRouter(prefix="/courses", tags=["课程"])


@router.get("", response_model=CourseListResponse)
async def get_courses(session_id: str = "default"):
    """获取课程列表"""
    client = get_client(session_id)
    xkgo = client.get_service(XkgoService)
    courses = await xkgo.get_selected_courses()
    return CourseListResponse(
        success=True,
        courses=courses,
        count=len(courses),
    )


@router.post("/search", response_model=CourseListResponse)
async def search_courses(course_code: str, session_id: str = "default"):
    """搜索课程"""
    client = get_client(session_id)
    xkgo = client.get_service(XkgoService)
    courses = await xkgo.search_course(course_code)
    return CourseListResponse(
        success=True,
        courses=courses,
        count=len(courses),
    )


@router.post("/select", response_model=SelectCourseResponse)
async def select_course(request: SelectCourseRequest, session_id: str = "default"):
    """选课"""
    client = get_client(session_id)
    xkgo = client.get_service(XkgoService)
    try:
        status, message = await xkgo.submit_course(request.course_code)
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
