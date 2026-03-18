
"""
教务系统相关端点 (成绩、讲座等)
"""

from fastapi import APIRouter
from ..deps import get_client
from ..services.xkcts import XkctsService
from ..models import GradeListResponse, LectureListResponse

router = APIRouter(prefix="/xkcts", tags=["教务系统"])

@router.get("/grades", response_model=GradeListResponse)
async def get_grades(session_id: str = "default"):
    """获取所有成绩"""
    client = get_client(session_id)
    xkcts = client.get_service(XkctsService)
    grades = await xkcts.get_grades()
    return GradeListResponse(
        success=True,
        grades=grades,
        count=len(grades)
    )

@router.get("/lectures/humanity/record", response_model=LectureListResponse)
async def get_humanity_lectures_record(session_id: str = "default"):
    """获取人文讲座听课记录"""
    client = get_client(session_id)
    xkcts = client.get_service(XkctsService)
    lectures = await xkcts.get_lectures_humanity_record()
    return LectureListResponse(
        success=True,
        lectures=lectures,
        count=len(lectures)
    )

@router.get("/lectures/science/record", response_model=LectureListResponse)
async def get_science_lectures_record(session_id: str = "default"):
    """获取科学前沿讲座听课记录"""
    client = get_client(session_id)
    xkcts = client.get_service(XkctsService)
    lectures = await xkcts.get_lectures_science_record()
    return LectureListResponse(
        success=True,
        lectures=lectures,
        count=len(lectures)
    )

@router.get("/lectures/humanity/list", response_model=LectureListResponse)
async def get_humanity_lectures_list(session_id: str = "default"):
    """获取人文讲座预告列表"""
    client = get_client(session_id)
    xkcts = client.get_service(XkctsService)
    lectures = await xkcts.get_lectures_humanity_list()
    return LectureListResponse(
        success=True,
        lectures=lectures,
        count=len(lectures)
    )
