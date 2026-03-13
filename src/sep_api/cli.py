"""
命令行工具
"""

import asyncio
import sys

import click
from loguru import logger

from .client import SEPClient

# 配置日志
logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
)


@click.group()
def cli():
    """国科大教务系统 CLI 工具"""
    pass


@cli.command()
@click.option("--username", "-u", prompt=True, help="用户名")
@click.option("--password", "-p", prompt=True, hide_input=True, help="密码")
@click.option("--captcha", "-c", default="", help="验证码（可选，不提供则自动识别）")
def login(username: str, password: str, captcha: str):
    """登录国科大教务系统"""
    asyncio.run(_login(username, password, captcha))


async def _login(username: str, password: str, captcha: str):
    client = SEPClient()
    try:
        await client.initialize()

        if not captcha:
            click.echo("正在获取验证码...")
            image_bytes = await client.get_captcha()
            captcha = await client.recognize_captcha(image_bytes)
            click.echo(f"自动识别验证码: {captcha}")

        await client.login(username, password, captcha)

        user_info = client.user_info
        click.echo(f"\n登录成功！欢迎 {user_info['name']} ({user_info['student_id']})")
        click.echo(f"单位: {user_info['unit']}")

        # 保存客户端供后续命令使用
        client.close = lambda: None  # 禁用自动关闭
        global _logged_in_client
        _logged_in_client = client

    except Exception as e:
        click.echo(f"登录失败: {e}", err=True)
        await client.close()


_logged_in_client: SEPClient | None = None


@cli.command()
def courses():
    """查看已选课程"""
    asyncio.run(_courses())


async def _courses():
    global _logged_in_client
    if not _logged_in_client:
        click.echo("请先登录！使用: sep-api login", err=True)
        return

    try:
        await _logged_in_client.xkgo()
        course_list = _logged_in_client.courses

        if not course_list:
            click.echo("暂无已选课程")
            return

        click.echo(f"\n已选课程（共 {len(course_list)} 门）：\n")
        for i, course in enumerate(course_list, 1):
            click.echo(
                f"{i}. {course['课程名称']} - {course['主讲教师']} "
                f"({course['课程编码']}, {course['学分']}学分)"
            )

    except Exception as e:
        click.echo(f"获取课程失败: {e}", err=True)


@cli.command()
@click.argument("course_code")
def search(course_code: str):
    """搜索课程"""
    asyncio.run(_search(course_code))


async def _search(course_code: str):
    global _logged_in_client
    if not _logged_in_client:
        click.echo("请先登录！使用: sep-api login", err=True)
        return

    try:
        html = await _logged_in_client.select_course(course_code)
        courses = _logged_in_client.course_parser(html)

        if not courses:
            click.echo("未找到相关课程")
            return

        click.echo(f"\n搜索结果（共 {len(courses)} 条）：\n")
        for i, course in enumerate(courses, 1):
            click.echo(
                f"{i}. {course.get('课程名称', 'N/A')} - {course.get('主讲教师', 'N/A')} "
                f"({course.get('课程编码', 'N/A')}, {course.get('学分', 'N/A')}学分)"
            )

    except Exception as e:
        click.echo(f"搜索失败: {e}", err=True)


@cli.command()
@click.argument("course_id")
def select(course_id: str):
    """选课"""
    asyncio.run(_select(course_id))


async def _select(course_id: str):
    global _logged_in_client
    if not _logged_in_client:
        click.echo("请先登录！使用: sep-api login", err=True)
        return

    try:
        click.echo("正在提交选课请求...")
        status, message = await _logged_in_client.submit_course(course_id)

        if status == "SUCCESS":
            click.echo(f"选课成功！{message}")
        else:
            click.echo(f"选课失败: {message}", err=True)

    except Exception as e:
        click.echo(f"选课失败: {e}", err=True)


def main():
    """入口函数"""
    cli()


if __name__ == "__main__":
    main()