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
    课程编码: str
    课程编码链接: str
    课程名称: str
    课程名称链接: str
    课时: str
    学分: str
    学位课: str
    考试方式: str
    主讲教师: str
    教师链接: str
    跨学期课程: str


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


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str
    detail: Optional[str] = None