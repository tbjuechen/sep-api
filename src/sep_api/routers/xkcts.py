"""
教务系统相关端点 (成绩、讲座、课程评估)
"""

from fastapi import APIRouter
from loguru import logger

from ..deps import get_client
from ..models import GradeListResponse, LectureListResponse
from ..services.xkcts import XkctsService

router = APIRouter(prefix="/xkcts", tags=["教务系统"])


@router.get("/grades", response_model=GradeListResponse)
async def get_grades(session_id: str = "default"):
    """获取所有成绩"""
    client = get_client(session_id)
    xkcts = client.get_service(XkctsService)
    try:
        grades = await xkcts.get_grades()
        return GradeListResponse(success=True, grades=grades, count=len(grades))
    except Exception as e:
        logger.error(f"Failed to get grades: {e}")
        return GradeListResponse(success=False, grades=[], count=0)


@router.get("/lectures/humanity/record", response_model=LectureListResponse)
async def get_humanity_lectures_record(session_id: str = "default"):
    """获取人文讲座听课记录"""
    client = get_client(session_id)
    xkcts = client.get_service(XkctsService)
    try:
        lectures = await xkcts.get_lectures_humanity_record()
        return LectureListResponse(success=True, lectures=lectures, count=len(lectures))
    except Exception as e:
        logger.error(f"Failed to get humanity lecture records: {e}")
        return LectureListResponse(success=False, lectures=[], count=0)


@router.get("/lectures/science/record", response_model=LectureListResponse)
async def get_science_lectures_record(session_id: str = "default"):
    """获取科学前沿讲座听课记录"""
    client = get_client(session_id)
    xkcts = client.get_service(XkctsService)
    try:
        lectures = await xkcts.get_lectures_science_record()
        return LectureListResponse(success=True, lectures=lectures, count=len(lectures))
    except Exception as e:
        logger.error(f"Failed to get science lecture records: {e}")
        return LectureListResponse(success=False, lectures=[], count=0)


@router.get("/lectures/humanity/list", response_model=LectureListResponse)
async def get_humanity_lectures_list(session_id: str = "default"):
    """获取人文讲座预告列表"""
    client = get_client(session_id)
    xkcts = client.get_service(XkctsService)
    try:
        lectures = await xkcts.get_lectures_humanity_list()
        return LectureListResponse(success=True, lectures=lectures, count=len(lectures))
    except Exception as e:
        logger.error(f"Failed to get humanity lecture list: {e}")
        return LectureListResponse(success=False, lectures=[], count=0)


@router.get("/evaluations")
async def get_evaluations(session_id: str = "default"):
    """获取评估课程列表"""
    client = get_client(session_id)
    xkcts = client.get_service(XkctsService)
    try:
        evals = await xkcts.get_evaluation_list()
        return {"success": True, "evaluations": evals, "count": len(evals)}
    except Exception as e:
        logger.error(f"Failed to get evaluation list: {e}")
        return {"success": False, "evaluations": [], "count": 0}


@router.post("/evaluations/auto")
async def auto_evaluate(
    eval_path: str,
    comment: str = "非常满意的课程，老师讲解清晰，收获很大。",
    session_id: str = "default",
):
    """自动评估课程（全优）"""
    client = get_client(session_id)
    xkcts = client.get_service(XkctsService)
    try:
        success, message = await xkcts.auto_evaluate_course(eval_path, comment)
        return {"success": success, "message": message}
    except Exception as e:
        logger.error(f"Failed to auto evaluate: {e}")
        return {"success": False, "message": str(e)}
