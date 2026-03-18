"""
命令行工具 — 交互模式 + Agent 友好的子命令模式
"""

import asyncio
import json
import sys

import click
from loguru import logger

from .client import SEPAuthError, SEPClient, SEPTwoFactorAuthError, SESSION_FILE
from .services.xkcts import XkctsService
from .services.xkgo import XkgoService

logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
)

MAX_CAPTCHA_RETRIES = 5


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------


def _load_client() -> SEPClient:
    """从 session 文件恢复客户端"""
    if not SESSION_FILE.exists():
        raise click.ClickException("未找到会话文件，请先登录: sep-api login -u USER -p PASS")
    return SEPClient.restore_session()


def _save_client(client: SEPClient) -> None:
    """保存客户端会话到文件"""
    client.save_session()


# ---------------------------------------------------------------------------
# Core async operations
# ---------------------------------------------------------------------------


async def _do_login(username: str, password: str) -> SEPClient:
    """核心登录流程（含验证码重试），2FA 时在异常上挂 client 后 re-raise"""
    client = SEPClient()
    await client.initialize()

    for attempt in range(1, MAX_CAPTCHA_RETRIES + 1):
        image_bytes = await client.get_captcha()
        captcha = await client.recognize_captcha(image_bytes)
        logger.info(f"验证码识别 (第 {attempt} 次): {captcha}")

        try:
            await client.login(username, password, captcha)
            return client
        except SEPTwoFactorAuthError as e:
            e.client = client  # type: ignore[attr-defined]
            raise
        except SEPAuthError:
            if attempt < MAX_CAPTCHA_RETRIES:
                logger.warning("验证码错误，重试...")
            else:
                await client.close()
                raise

    await client.close()
    raise SEPAuthError("验证码识别多次失败")


async def _do_courses(client: SEPClient) -> list[dict]:
    xkgo = client.get_service(XkgoService)
    return await xkgo.get_selected_courses()


async def _do_search(client: SEPClient, code: str) -> list[dict]:
    xkgo = client.get_service(XkgoService)
    return await xkgo.search_course(code)


async def _do_select(client: SEPClient, course_id: str) -> tuple[str, str | None]:
    xkgo = client.get_service(XkgoService)
    return await xkgo.submit_course(course_id)


async def _do_grades(client: SEPClient) -> list[dict]:
    xkcts = client.get_service(XkctsService)
    return await xkcts.get_grades()


async def _do_lectures_hum_rec(client: SEPClient) -> list[dict]:
    xkcts = client.get_service(XkctsService)
    return await xkcts.get_lectures_humanity_record()


async def _do_lectures_sci_rec(client: SEPClient) -> list[dict]:
    xkcts = client.get_service(XkctsService)
    return await xkcts.get_lectures_science_record()


async def _do_lectures_hum_list(client: SEPClient) -> list[dict]:
    xkcts = client.get_service(XkctsService)
    return await xkcts.get_lectures_humanity_list()


# ---------------------------------------------------------------------------
# Rich display helpers (only imported when called)
# ---------------------------------------------------------------------------


def _print_welcome_banner() -> None:
    from rich.console import Console
    from rich.panel import Panel

    Console().print(
        Panel(
            "[bold cyan]国科大教务系统 CLI[/bold cyan]",
            subtitle="sep-api",
            expand=False,
        )
    )


def _print_user_card(client: SEPClient) -> None:
    from rich.console import Console
    from rich.panel import Panel

    info = f"[bold]{client.name}[/bold]\n学号: {client.student_id}\n单位: {client.unit}"
    Console().print(Panel(info, title="用户信息", expand=False))


def _render_course_table(
    data: list[dict], title: str = "数据列表", exclude_cols: list[str] = None
) -> None:
    from rich.console import Console
    from rich.table import Table

    if not data:
        Console().print("[yellow]暂无数据[/yellow]")
        return

    # 默认排除一些对 CLI 没意义的列
    default_exclude = ["操作区", "评估状态"]
    if exclude_cols:
        default_exclude.extend(exclude_cols)

    table = Table(title=title, show_lines=True)
    
    # 确定要显示的列头，自动排除隐藏列和链接列
    all_headers = list(data[0].keys())
    visible_headers = [
        h for h in all_headers 
        if h and h not in default_exclude and "链接" not in h
    ]

    for h in visible_headers:
        table.add_column(h)
    
    for row in data:
        table.add_row(*[str(row.get(h, "")) for h in visible_headers])
    
    Console().print(table)


# ---------------------------------------------------------------------------
# Interactive mode (rich + InquirerPy)
# ---------------------------------------------------------------------------


async def _interactive_login() -> SEPClient:
    from InquirerPy import inquirer

    username = await inquirer.text(message="用户名:").execute_async()
    password = await inquirer.secret(message="密码:").execute_async()

    try:
        client = await _do_login(username, password)
    except SEPTwoFactorAuthError as e:
        client: SEPClient = e.client  # type: ignore[attr-defined]
        from rich.console import Console

        Console().print(f"[yellow]需要二次验证 — 邮箱: {e.email}  手机: {e.phone}[/yellow]")

        method = await inquirer.select(
            message="选择验证方式:",
            choices=["邮箱验证码", "手机验证码"],
        ).execute_async()

        if method == "手机验证码":
            await client.send_phone_code()
            code = await inquirer.text(message="请输入手机验证码:").execute_async()
            success = await client.verify_two_factor(phone_code=code)
        else:
            await client.send_email_code()
            code = await inquirer.text(message="请输入邮箱验证码:").execute_async()
            success = await client.verify_two_factor(email_code=code)

        if not success:
            await client.close()
            raise SEPAuthError("二次验证失败")

    _save_client(client)
    return client


async def _interactive_main() -> None:
    from InquirerPy import inquirer

    _print_welcome_banner()

    client: SEPClient | None = None

    # 尝试恢复会话
    if SESSION_FILE.exists():
        try:
            client = _load_client()
            logger.info("从会话文件恢复...")
            if not await client.validate_session():
                logger.warning("会话已过期")
                await client.close()
                client = None
                SESSION_FILE.unlink(missing_ok=True)
        except Exception:
            client = None

    if client is None:
        client = await _interactive_login()

    _print_user_card(client)

    # 主菜单循环
    menu_choices = [
        "选课管理",
        "成绩与评估",
        "讲座管理",
        "退出登录",
        "退出",
    ]

    try:
        while True:
            action = await inquirer.select(message="请选择操作:", choices=menu_choices).execute_async()

            if action == "选课管理":
                sub_action = await inquirer.select(
                    message="请选择操作:",
                    choices=["查看已选课程", "搜索课程", "快速选课 (输入 ID)", "返回"],
                ).execute_async()

                try:
                    if sub_action == "查看已选课程":
                        courses = await _do_courses(client)
                        _render_course_table(courses, title=f"已选课程 ({len(courses)} 门)")
                    elif sub_action == "搜索课程":
                        code = await inquirer.text(message="课程编码:").execute_async()
                        if code.strip():
                            results = await _do_search(client, code.strip())
                            _render_course_table(results, title=f"搜索结果 ({len(results)} 条)")
                    elif sub_action == "快速选课 (输入 ID)":
                        course_id = await inquirer.text(message="课程 ID:").execute_async()
                        if course_id.strip():
                            confirm = await inquirer.confirm(
                                message=f"确认选课 ID={course_id.strip()}?", default=False
                            ).execute_async()
                            if confirm:
                                status, msg = await _do_select(client, course_id.strip())
                                from rich.console import Console

                                if status == "SUCCESS":
                                    Console().print(f"[green]选课成功: {msg}[/green]")
                                else:
                                    Console().print(f"[red]选课失败: {msg}[/red]")
                except Exception as e:
                    logger.error(f"操作失败: {e}")

            elif action == "成绩与评估":
                sub_action = await inquirer.select(
                    message="请选择操作:",
                    choices=["查询所有成绩", "课程评估 (一键全优)", "返回"],
                ).execute_async()

                try:
                    xkcts = client.get_service(XkctsService)
                    if sub_action == "查询所有成绩":
                        grades = await _do_grades(client)
                        _render_course_table(grades, title=f"所有成绩 ({len(grades)} 门)")
                    elif sub_action == "课程评估 (一键全优)":
                        eval_list = await xkcts.get_evaluation_list()
                        to_eval = [c for c in eval_list if "评估" in c.get("状态", "") and c.get("评估链接")]
                        
                        if not to_eval:
                            from rich.console import Console
                            Console().print("[green]没有需要评估的课程。[/green]")
                        else:
                            _render_course_table(to_eval, title="待评估课程")
                            confirm = await inquirer.confirm(
                                message=f"确认自动评估这 {len(to_eval)} 门课程 (全优+好评)?", default=True
                            ).execute_async()
                            
                            if confirm:
                                from rich.progress import track
                                for c in track(to_eval, description="正在评估..."):
                                    success, msg = await xkcts.auto_evaluate_course(c["评估链接"])
                                    if not success:
                                        logger.error(f"评估 {c['课程名称']} 失败: {msg}")
                                logger.info("评估任务完成。")
                except Exception as e:
                    logger.error(f"操作失败: {e}")

            elif action == "讲座管理":
                sub_action = await inquirer.select(
                    message="请选择操作:",
                    choices=["人文讲座记录", "科学前沿讲座记录", "人文讲座报名列表", "返回"],
                ).execute_async()

                try:
                    if sub_action == "人文讲座记录":
                        data = await _do_lectures_hum_rec(client)
                        _render_course_table(data, title="人文讲座听课记录")
                    elif sub_action == "科学前沿讲座记录":
                        data = await _do_lectures_sci_rec(client)
                        _render_course_table(data, title="科学前沿讲座听讲情况")
                    elif sub_action == "人文讲座报名列表":
                        data = await _do_lectures_hum_list(client)
                        _render_course_table(data, title="人文讲座报名预告")
                except Exception as e:
                    logger.error(f"获取讲座数据失败: {e}")

            elif action == "退出登录":
                SESSION_FILE.unlink(missing_ok=True)
                await client.close()
                logger.info("已退出登录")
                client = await _interactive_login()
                _print_user_card(client)

            elif action == "退出":
                break
    finally:
        await client.close()


# ---------------------------------------------------------------------------
# Click CLI
# ---------------------------------------------------------------------------


@click.group(invoke_without_command=True)
@click.option("--json", "json_output", is_flag=True, default=False, help="JSON 输出（agent 友好）")
@click.pass_context
def cli(ctx: click.Context, json_output: bool) -> None:
    """国科大教务系统 CLI 工具

    不带子命令运行进入交互模式，带子命令供脚本/agent 调用。
    """
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_output
    if ctx.invoked_subcommand is None:
        asyncio.run(_interactive_main())


@cli.command()
@click.option("--username", "-u", required=True, help="用户名")
@click.option("--password", "-p", required=True, help="密码")
def login(username: str, password: str) -> None:
    """非交互登录，保存 session"""
    asyncio.run(_cli_login(username, password))


async def _cli_login(username: str, password: str) -> None:
    try:
        client = await _do_login(username, password)
        _save_client(client)
        info = client.user_info
        click.echo(json.dumps({"success": True, "user": info}, ensure_ascii=False))
        await client.close()
    except SEPTwoFactorAuthError as e:
        client: SEPClient = e.client  # type: ignore[attr-defined]
        _save_client(client)
        click.echo(
            json.dumps(
                {
                    "success": False,
                    "error": "two_factor_required",
                    "email": e.email,
                    "phone": e.phone,
                },
                ensure_ascii=False,
            ),
            err=True,
        )
        await client.close()
        sys.exit(2)
    except SEPAuthError as e:
        click.echo(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False), err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def courses(ctx: click.Context) -> None:
    """查看已选课程"""
    asyncio.run(_cli_courses(ctx.obj["json"]))


async def _cli_courses(json_output: bool) -> None:
    client = _load_client()
    try:
        course_list = await _do_courses(client)
        if json_output:
            click.echo(json.dumps(course_list, ensure_ascii=False))
        else:
            _render_course_table(course_list, title=f"已选课程 ({len(course_list)} 门)")
    finally:
        await client.close()


@cli.command()
@click.argument("course_code")
@click.pass_context
def search(ctx: click.Context, course_code: str) -> None:
    """搜索课程"""
    asyncio.run(_cli_search(course_code, ctx.obj["json"]))


async def _cli_search(course_code: str, json_output: bool) -> None:
    client = _load_client()
    try:
        results = await _do_search(client, course_code)
        if json_output:
            click.echo(json.dumps(results, ensure_ascii=False))
        else:
            _render_course_table(results, title=f"搜索结果 ({len(results)} 条)")
    finally:
        await client.close()


@cli.command()
@click.pass_context
def select(ctx: click.Context, course_id: str) -> None:
    """选课"""
    asyncio.run(_cli_select(course_id, ctx.obj["json"]))


async def _cli_select(course_id: str, json_output: bool) -> None:
    client = _load_client()
    try:
        status, msg = await _do_select(client, course_id)
        if json_output:
            click.echo(json.dumps({"status": status, "message": msg}, ensure_ascii=False))
        else:
            if status == "SUCCESS":
                click.echo(f"选课成功: {msg}")
            else:
                click.echo(f"选课失败: {msg}", err=True)
                sys.exit(1)
    finally:
        await client.close()


@cli.command()
@click.pass_context
def grades(ctx: click.Context) -> None:
    """查看所有成绩"""
    asyncio.run(_cli_grades(ctx.obj["json"]))


async def _cli_grades(json_output: bool) -> None:
    client = _load_client()
    try:
        data = await _do_grades(client)
        if json_output:
            click.echo(json.dumps(data, ensure_ascii=False))
        else:
            _render_course_table(data, title=f"所有成绩 ({len(data)} 门)")
    finally:
        await client.close()


@cli.command()
@click.option(
    "--type",
    "-t",
    "type_",
    type=click.Choice(["hum-rec", "sci-rec", "hum-list"]),
    default="hum-rec",
    help="讲座类型",
)
@click.pass_context
def lectures(ctx: click.Context, type_: str) -> None:
    """查看讲座信息"""
    asyncio.run(_cli_lectures(type_, ctx.obj["json"]))


async def _cli_lectures(type_: str, json_output: bool) -> None:
    client = _load_client()
    try:
        if type_ == "hum-rec":
            data = await _do_lectures_hum_rec(client)
            title = "人文讲座听课记录"
        elif type_ == "sci-rec":
            data = await _do_lectures_sci_rec(client)
            title = "科学前沿讲座听讲情况"
        else:
            data = await _do_lectures_hum_list(client)
            title = "人文讲座报名预告"

        if json_output:
            click.echo(json.dumps(data, ensure_ascii=False))
        else:
            _render_course_table(data, title=title)
    finally:
        await client.close()


@cli.command()
@click.option("--host", default="0.0.0.0", help="监听地址")
@click.option("--port", default=8000, type=int, help="监听端口")
@click.option("--reload", "reload_", is_flag=True, default=False, help="热重载")
def serve(host: str, port: int, reload_: bool) -> None:
    """启动 API 服务器"""
    import uvicorn

    uvicorn.run("sep_api.app:app", host=host, port=port, reload=reload_)


def main() -> None:
    """入口函数"""
    cli()


if __name__ == "__main__":
    main()
