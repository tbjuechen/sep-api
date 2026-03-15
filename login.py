#!/usr/bin/env python
"""交互式登录脚本"""
import asyncio
import json
import sys
from sep_api.client import SEPClient, SEPAuthError, SEPTwoFactorAuthError

MAX_CAPTCHA_RETRIES = 5


async def main():
    print("=" * 50)
    print("  国科大教务系统登录")
    print("=" * 50)

    username = sys.argv[1] if len(sys.argv) > 1 else None
    password = sys.argv[2] if len(sys.argv) > 2 else None

    if not username:
        username = input("\n用户名: ").strip()
    if not password:
        password = input("密码: ").strip()

    client = SEPClient()
    try:
        print("\n[1/5] 初始化会话...")
        await client.initialize()
        print("   ✓")

        for attempt in range(1, MAX_CAPTCHA_RETRIES + 1):
            print(f"\n[2/5] 获取验证码 (第 {attempt} 次)...")
            image_bytes = await client.get_captcha()
            captcha = await client.recognize_captcha(image_bytes)
            with open("captcha.png", "wb") as f:
                f.write(image_bytes)
            print(f"   验证码: {captcha} (已保存到 captcha.png)")

            print("\n[3/5] 登录中...")
            try:
                await client.login(username, password, captcha)
                break  # 登录成功
            except SEPTwoFactorAuthError as e:
                print("\n   ⚠️ 需要二次验证!")
                print("   ────────────────────────")
                print(f"   1. 邮箱: {e.email}")
                print(f"   2. 手机: {e.phone}")
                print("   ────────────────────────")
                choice = input("\n   请选择验证方式 (1=邮箱, 2=手机): ").strip()

                if choice == "2":
                    print("   发送手机验证码...")
                    await client.send_phone_code()
                    code = input("   请输入手机验证码: ").strip()
                    success = await client.verify_two_factor(phone_code=code)
                else:
                    print("   发送邮箱验证码...")
                    await client.send_email_code()
                    code = input("   请输入邮箱验证码: ").strip()
                    success = await client.verify_two_factor(email_code=code)

                if not success:
                    print("\n   ❌ 二次验证失败")
                    sys.exit(1)
                print("   ✓ 二次验证成功")
                break
            except SEPAuthError as e:
                if attempt < MAX_CAPTCHA_RETRIES:
                    print(f"   ✗ {e}，重试...")
                else:
                    raise

        print("\n[4/5] 登录成功!")
        print(f"   姓名: {client.name}")
        print(f"   学号: {client.student_id}")
        print(f"   单位: {client.unit}")

        # 保存会话
        session_data = {
            "username": username,
            "cookies": dict(client.session.cookies),
            "user_info": client.user_info,
        }
        with open(".sep_session.json", "w") as f:
            json.dump(session_data, f, ensure_ascii=False)
        print("\n[5/5] 会话已保存到 .sep_session.json")

        # 获取课程
        await client.xkgo()
        print(f"\n已选课程: {len(client.courses)} 门")
        for c in client.courses[:5]:
            print(f"  - {c['课程名称']}")

        print("\n" + "=" * 50)
        print("  完成!")
        print("=" * 50)

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
