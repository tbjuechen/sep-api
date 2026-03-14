"""
国科大教务系统 API 客户端
"""

import base64
import re
import time
from typing import Optional

import httpx
from loguru import logger
from lxml import etree

from .captcha import CaptchaHandler


class SEPAuthError(Exception):
    """认证错误"""
    pass


class SEPTwoFactorAuthError(SEPAuthError):
    """二次验证错误，需要邮箱或手机验证码"""
    def __init__(self, email: str, phone: str, user_id: str, user_name: str):
        self.email = email
        self.phone = phone
        self.user_id = user_id
        self.user_name = user_name
        super().__init__(f"需要二次验证 - 邮箱: {email}, 手机: {phone}")


class SEPClient:
    """国科大教务系统客户端"""

    def __init__(self):
        self.session = httpx.AsyncClient(
            headers={
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "accept-encoding": "gzip, deflate, br, zstd",
                "accept-language": "zh-CN,zh;q=0.9",
                "cache-control": "max-age=0",
                "connection": "keep-alive",
                "sec-ch-ua": '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-dest": "document",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "same-origin",
                "sec-fetch-user": "?1",
                "upgrade-insecure-requests": "1",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            },
            timeout=30.0,
        )
        self.captcha_handler = CaptchaHandler()
        self._captcha_result: Optional[str] = None
        self._two_factor_data: Optional[dict] = None
        self.name: Optional[str] = None
        self.student_id: Optional[str] = None
        self.unit: Optional[str] = None
        self.courses: list = []
        self._is_logged_in = False

    async def initialize(self) -> None:
        """初始化会话，访问首页"""
        await self.session.get("https://sep.ucas.ac.cn/")

    async def get_captcha(self) -> bytes:
        """获取验证码图片"""
        response = await self.session.get("https://sep.ucas.ac.cn/changePic")
        response.raise_for_status()
        return response.content

    async def recognize_captcha(self, image_bytes: bytes) -> str:
        """识别验证码"""
        self._captcha_result = await self.captcha_handler.recognize(image_bytes)
        logger.debug(f"OCR result: {self._captcha_result}")
        return self._captcha_result

    @staticmethod
    def encrypt_password_rsa(password: str) -> str:
        """使用 RSA 公钥加密密码"""
        rsa_pub_key = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAxG1zt7VW/VNk1KJC7Auo
InrMZKTf0h6S6xBaROgCz8F3xdEIwdTBGrjUKIhIFCeDr6esfiVxUpdCdiRtqaCS
9IdXO+9Fs2l6fx6oGkAA9pnxIWL7bw5vAxyK+liu7BToMFhUdiyRdB6erC1g/fwD
VBywCWhY4wCU2/TSsTBDQhuGZzy+hmZGEB0sqgZbbJpeosW87dNZFomn/uGhfCDJ
zswjS/x0OXD9yyk5TEq3QEvx5pWCcBJqAoBfDDQy5eT3RR5YBGDJODHqW1c2Owwd
rybEEXKI9RCZmsNyIs2eZn1z1Cw1AdR+owdXqbJf9AnM3e1CN8GcpWLDyOnaRymL
gQIDAQAB
-----END PUBLIC KEY-----"""

        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.backends import default_backend

        public_key = serialization.load_pem_public_key(
            rsa_pub_key.encode(), backend=default_backend()
        )
        encrypted = public_key.encrypt(
            password.encode(),
            padding.PKCS1v15(),
        )
        return base64.b64encode(encrypted).decode()

    async def login(
        self, username: str, password: str, captcha: Optional[str] = None,
        email_code: Optional[str] = None, phone_code: Optional[str] = None,
        trust_device: bool = True
    ) -> str:
        """登录（支持二次验证）"""
        if not captcha:
            captcha = self._captcha_result

        api_url = "https://sep.ucas.ac.cn/slogin"
        logger.debug(f"Encrypt pwd: {self.encrypt_password_rsa(password)}")

        data = {
            "userName": username,
            "pwd": self.encrypt_password_rsa(password),
            "loginFrom": "",
            "certCode": captcha,
            "sb": "sb",
        }

        response = await self.session.post(
            api_url, data=data, follow_redirects=False
        )
        if response.status_code >= 400:
            response.raise_for_status()

        # 检查是否需要二次验证
        if response.status_code in (301, 302, 303, 307, 308):
            location = response.headers.get("Location", "")
            if "userVisit" in location:
                # 需要二次验证
                verify_page = await self.session.get(f"https://sep.ucas.ac.cn{location}")
                self._parse_two_factor(verify_page.text)
                logger.info(f"需要二次验证 - 邮箱: {self._two_factor_data.get('email')}, 手机: {self._two_factor_data.get('phone')}")

                if email_code or phone_code:
                    await self._submit_two_factor(email_code, phone_code, trust_device)
                else:
                    raise SEPTwoFactorAuthError(
                        email=self._two_factor_data.get("email", ""),
                        phone=self._two_factor_data.get("phone", ""),
                        user_id=self._two_factor_data.get("user_id", ""),
                        user_name=self._two_factor_data.get("user_name", "")
                    )

        # 跟随重定向
        response = await self.session.get("https://sep.ucas.ac.cn/", follow_redirects=True)
        self._parse_mainpage(response.text)
        self._is_logged_in = True
        return response.text

    def _parse_two_factor(self, page: str) -> None:
        """解析二次验证页面"""
        if not page:
            return

        tree = etree.HTML(page)
        if tree is None:
            return

        email_form = tree.xpath("//form[@action='/user/doUserVisit']")
        if email_form:
            self._two_factor_data = {
                "user_id": email_form[0].xpath(".//input[@name='userId']/@value")[0],
                "user_name": email_form[0].xpath(".//input[@name='userName']/@value")[0],
                "mobile": email_form[0].xpath(".//input[@name='mobile']/@value")[0],
            }

            email_text = tree.xpath("//div[contains(text(), '邮箱：')]/text()")
            phone_text = tree.xpath("//div[contains(text(), '手机号：')]/text()")

            if email_text:
                self._two_factor_data["email"] = email_text[0].replace("邮箱：", "").strip()
            if phone_text:
                self._two_factor_data["phone"] = phone_text[0].replace("手机号：", "").strip()

    async def send_email_code(self) -> bool:
        """发送邮箱验证码"""
        if not self._two_factor_data:
            raise SEPAuthError("无需二次验证或会话已过期")

        data = {
            "userId": self._two_factor_data["user_id"],
            "userName": self._two_factor_data["user_name"],
            "mobile": self._two_factor_data["mobile"],
        }
        await self.session.post("https://sep.ucas.ac.cn/user/sendMailCode", data=data)
        logger.info("邮箱验证码已发送")
        return True

    async def send_phone_code(self) -> bool:
        """发送手机验证码"""
        if not self._two_factor_data:
            raise SEPAuthError("无需二次验证或会话已过期")

        data = {
            "userId": self._two_factor_data["user_id"],
            "userName": self._two_factor_data["user_name"],
            "mobile": self._two_factor_data["mobile"],
        }
        await self.session.post("https://sep.ucas.ac.cn/user/sendPhoneCode", data=data)
        logger.info("手机验证码已发送")
        return True

    async def verify_two_factor(
        self,
        email_code: Optional[str] = None,
        phone_code: Optional[str] = None,
        trust_device: bool = True
    ) -> bool:
        """提交二次验证"""
        return await self._submit_two_factor(email_code, phone_code, trust_device)

    async def _submit_two_factor(
        self,
        email_code: Optional[str] = None,
        phone_code: Optional[str] = None,
        trust_device: bool = True
    ) -> bool:
        """提交二次验证"""
        if not self._two_factor_data:
            raise SEPAuthError("无需二次验证或会话已过期")

        if email_code:
            verify_data = {
                "userId": self._two_factor_data["user_id"],
                "userName": self._two_factor_data["user_name"],
                "mobile": self._two_factor_data["mobile"],
                "yz": email_code,
                "trustDevice": "1" if trust_device else "0",
            }
            response = await self.session.post(
                "https://sep.ucas.ac.cn/user/doUserVisit",
                data=verify_data,
                follow_redirects=True
            )
        elif phone_code:
            verify_data = {
                "userId": self._two_factor_data["user_id"],
                "userName": self._two_factor_data["user_name"],
                "mobile": self._two_factor_data["mobile"],
                "yzPhone": phone_code,
                "trustDevice": "1" if trust_device else "0",
            }
            response = await self.session.post(
                "https://sep.ucas.ac.cn/user/doUserVisitPhone",
                data=verify_data,
                follow_redirects=True
            )
        else:
            raise SEPAuthError("请提供邮箱或手机验证码")

        if "userVisit" in str(response.url):
            logger.error("二次验证失败")
            return False

        response = await self.session.get("https://sep.ucas.ac.cn/", follow_redirects=True)
        self._parse_mainpage(response.text)
        self._is_logged_in = True
        self._two_factor_data = None
        logger.info(f"登录成功！欢迎 {self.name} ({self.student_id})")
        return True

    def _parse_mainpage(self, page: str) -> None:
        """解析首页"""
        try:
            tree = etree.HTML(page)

            # 方式1: 查找学生卡片
            stu_card = tree.xpath("//div[contains(@class, 'stude')]")
            if stu_card:
                # 姓名
                name = stu_card[0].xpath(".//p[@class='home']//text()")
                self.name = "".join(name).strip() if name else "未找到姓名"

                # 学号
                student_id = stu_card[0].xpath(".//a[contains(@href, '/selectNumber')]/text()")
                if not student_id:
                    student_id = stu_card[0].xpath(".//a[contains(@href, 'selectNumber')]/text()")
                self.student_id = student_id[0].strip() if student_id else "未找到学号"

                # 单位
                unit = stu_card[0].xpath("./p[position() = last()]/text()")
                if not unit:
                    unit = stu_card[0].xpath(".//div[contains(@class, 'character')]//text()")
                self.unit = "".join(unit).strip() if unit else "未找到单位"

                logger.info(f"欢迎 {self.name} ({self.student_id})")
                return

            # 方式2: 从整个页面搜索
            import re
            name_match = re.search(r'class="home"[^>]*>\s*(\S+)', page)
            if name_match:
                self.name = name_match.group(1).strip()

            stu_id_match = re.search(r'number=(\d+)', page)
            if stu_id_match:
                self.student_id = stu_id_match.group(1)

            if self.name:
                logger.info(f"欢迎 {self.name} ({self.student_id})")
            else:
                logger.warning("未找到用户信息")
        except Exception as e:
            logger.error(f"Error parsing main page: {e}")

    @property
    def is_logged_in(self) -> bool:
        return self._is_logged_in

    @property
    def two_factor_info(self) -> Optional[dict]:
        return self._two_factor_data

    async def xkgo(self) -> str:
        """访问选课页面"""
        api_url = "https://sep.ucas.ac.cn/portal/site/524/2412"
        response = await self.session.get(api_url, follow_redirects=True)
        response.raise_for_status()

        match = re.search(r"window\.location\.href\s*=\s*'([^']+)'", response.text)
        if match:
            logger.debug(f"Redirecting to: {match.group(1)}")
            response = await self.session.get(match.group(1), follow_redirects=True)
            response.raise_for_status()

        self.courses = self._parse_xkgo(response.text)
        return response.text

    def _parse_xkgo(self, page: str) -> list:
        """解析选课页面课程列表"""
        tree = etree.HTML(page)
        courses = []

        for row in tree.xpath("//table/tbody/tr"):
            cols = row.xpath("./td")
            if len(cols) < 8:
                continue

            course = {
                "课程编码": cols[0].xpath(".//a/text()")[0] if cols[0].xpath(".//a/text()") else "",
                "课程名称": cols[1].xpath(".//a/text()")[0] if cols[1].xpath(".//a/text()") else "",
                "课时": cols[2].text.strip() if cols[2].text else "",
                "学分": cols[3].text.strip() if cols[3].text else "",
                "学位课": cols[4].text.strip() if cols[4].text else "",
                "考试方式": cols[5].text.strip() if cols[5].text else "",
                "主讲教师": cols[6].xpath(".//a/text()")[0] if cols[6].xpath(".//a/text()") else "",
                "跨学期课程": cols[7].text.strip() if cols[7].text else "",
            }
            courses.append(course)

        self.courses = courses
        return courses

    async def select_course(self, course_code: str) -> str:
        """搜索课程"""
        api_url = "http://xkgo.ucas.ac.cn:3000/courseManage/selectCourse"
        data = {
            "type": "",
            "deptIds1": "&deptIds=979&deptIds=244&deptIds=245&deptIds=246&deptIds=247&deptIds=248&deptIds=249&deptIds=250&deptIds=251&deptIds=252&deptIds=253",
            "courseType1": "&courseType=1&courseType=2&courseType=3",
            "courseCode": course_code,
            "courseName": "",
        }
        response = await self.session.post(api_url, data=data)
        response.raise_for_status()
        return response.text

    def course_parser(self, html: str) -> list:
        """解析课程搜索结果"""
        tree = etree.HTML(html)
        headers = tree.xpath("//table/thead/tr/th/text()")

        result = []
        for tr in tree.xpath("//table/tbody[@id='courseinfo']/tr"):
            cells = tr.xpath("./td")
            row_data = {}
            for header, td in zip(headers, cells):
                text = "".join(td.xpath(".//text()")).strip()
                row_data[header] = text
            row_data["选课"] = tr.xpath(".//input/@value")[0]
            result.append(row_data)

        return result

    async def get_submit_captcha(self) -> bytes:
        """获取选课验证码"""
        timestamp = int(time.time() * 1000)
        api_url = "http://xkgo.ucas.ac.cn:3000/captchaImage"
        response = await self.session.get(api_url, params={"_": timestamp})
        response.raise_for_status()
        img_data = base64.b64decode(response.text.split(",")[1])
        await self.recognize_captcha(img_data)
        return img_data

    async def submit_course(self, course_id: str) -> tuple:
        """提交选课"""
        await self.get_submit_captcha()

        api_url = "http://xkgo.ucas.ac.cn:3000/courseManage/saveCourse"
        data = {
            "vcode": self._captcha_result,
            "deptIds": 979,
            "deptIds": 244,
            "deptIds": 245,
            "deptIds": 246,
            "deptIds": 247,
            "deptIds": 248,
            "deptIds": 249,
            "deptIds": 250,
            "deptIds": 251,
            "deptIds": 252,
            "deptIds": 253,
            "sids": course_id,
        }
        response = await self.session.post(api_url, data=data)
        response.raise_for_status()

        return self._parse_status(response.text)

    def _parse_status(self, page: str) -> tuple:
        """解析选课结果"""
        tree = etree.HTML(page)

        success = tree.xpath('//label[@id="loginSuccess"]/text()')
        if success and success[0].strip():
            return "SUCCESS", success[0].strip()

        error = tree.xpath('//label[@id="loginError"]/text()')
        if error and error[0].strip():
            return "ERROR", error[0].strip()

        return "unknown", None

    async def close(self) -> None:
        """关闭会话"""
        await self.session.aclose()

    @property
    def user_info(self) -> dict:
        """获取用户信息"""
        return {
            "name": self.name,
            "student_id": self.student_id,
            "unit": self.unit,
        }