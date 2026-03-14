"""检查登录后页面"""
import asyncio
import httpx

async def main():
    session = httpx.AsyncClient(
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    )

    try:
        # 1. 初始化
        await session.get("https://sep.ucas.ac.cn/")
        print(f"Step 1: Cookies: {dict(session.cookies)}")

        # 2. 获取验证码
        resp = await session.get("https://sep.ucas.ac.cn/changePic")

        from sep_api.captcha import CaptchaHandler
        handler = CaptchaHandler()
        captcha = await handler.recognize(resp.content)
        print(f"Step 2: 验证码: {captcha}")

        # 3. 登录
        from sep_api.client import SEPClient
        pwd = SEPClient.encrypt_password_rsa("Aa20030613!")

        # 不自动跟随重定向，看看跳转哪里
        resp = await session.post(
            "https://sep.ucas.ac.cn/slogin",
            data={"userName": "wangru251@mails.ucas.ac.cn", "pwd": pwd, "certCode": captcha, "sb": "sb"},
            follow_redirects=False
        )

        print(f"Step 3: 登录响应 Status: {resp.status_code}")
        print(f"Step 3: Location: {resp.headers.get('Location', 'N/A')}")

        # 跟随重定向
        resp = await session.get("https://sep.ucas.ac.cn/", follow_redirects=True)
        print(f"Step 4: 最终URL: {resp.url}")

        # 保存页面内容
        with open("home_page.html", "w", encoding="utf-8") as f:
            f.write(resp.text)
        print(f"Step 5: 页面已保存, 长度: {len(resp.text)}")

        # 解析用户信息
        from lxml import etree
        tree = etree.HTML(resp.text)

        # 尝试多种方式找用户信息
        print("\n尝试查找用户信息...")

        # 方法1: 原始方式
        stu_card = tree.xpath("//div[@class='card card-body people stude']")
        print(f"  方法1 (card stude): {len(stu_card)} 个")

        # 方法2: 查找任何包含学生信息的元素
        cards = tree.xpath("//div[contains(@class, 'card')]")
        print(f"  方法2 (所有card): {len(cards)} 个")

        # 方法3: 查找用户信息相关文本
        import re
        name_match = re.search(r'姓名[：:]\s*(\S+)', resp.text)
        if name_match:
            print(f"  方法3 (姓名): {name_match.group(1)}")

        # 查找学号
        stu_id_match = re.search(r'学号[：:]\s*(\S+)', resp.text)
        if stu_id_match:
            print(f"  方法3 (学号): {stu_id_match.group(1)}")

        # 方法4: 查找页面上所有可能的名字
        names = tree.xpath("//span[contains(@class, 'name')]//text()")
        print(f"  方法4 (span.name): {names}")

        # 查看页面标题
        title = tree.xpath("//title/text()")
        print(f"  页面标题: {title}")

    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await session.aclose()

asyncio.run(main())