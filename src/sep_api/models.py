"""
Pydantic 数据模型
"""

from typing import Optional

from pydantic import BaseModel


class UserInfo(BaseModel):
    """用户信息"""

    name: Optional[str] = None
    student_id: Optional[str] = None
    unit: Optional[str] = None


class LoginRequest(BaseModel):
    """登录请求"""

    username: str
    password: str
    captcha: Optional[str] = None


class LoginResponse(BaseModel):
    """登录响应"""

    success: bool
    message: str
    user: Optional[UserInfo] = None


class Course(BaseModel):
    """课程信息"""

    课程编码: Optional[str] = None
    课程编码链接: Optional[str] = None
    课程名称: Optional[str] = None
    课程名称链接: Optional[str] = None
    课时: Optional[str] = None
    学分: Optional[str] = None
    学位课: Optional[str] = None
    考试方式: Optional[str] = None
    主讲教师: Optional[str] = None
    教师链接: Optional[str] = None
    跨学期课程: Optional[str] = None

    class Config:
        """配置"""

        extra = "allow"


class CourseListResponse(BaseModel):
    """课程列表响应"""

    success: bool
    courses: list[Course]
    count: int


class SelectCourseRequest(BaseModel):
    """选课请求"""

    course_code: str


class SelectCourseResponse(BaseModel):
    """选课响应"""

    success: bool
    status: str
    message: str


class CaptchaResponse(BaseModel):
    """验证码响应"""

    success: bool
    image_base64: str
    message: str = "请输入验证码"


class Grade(BaseModel):
    """成绩信息"""

    课程编码: Optional[str] = None
    课程名称: Optional[str] = None
    学分: Optional[str] = None
    成绩: Optional[str] = None
    性质: Optional[str] = None
    学年: Optional[str] = None
    学期: Optional[str] = None

    class Config:
        """配置"""

        extra = "allow"


class GradeListResponse(BaseModel):
    """成绩列表响应"""

    success: bool
    grades: list[Grade]
    count: int


class Lecture(BaseModel):
    """讲座信息"""

    讲座名称: Optional[str] = None
    主讲人: Optional[str] = None
    讲座地点: Optional[str] = None
    讲座时间: Optional[str] = None
    学分: Optional[str] = None

    class Config:
        """配置"""

        extra = "allow"


class LectureListResponse(BaseModel):
    """讲座列表响应"""

    success: bool
    lectures: list[Lecture]
    count: int
