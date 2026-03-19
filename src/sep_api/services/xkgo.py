"""
选课子系统 service (xkgo.ucas.ac.cn:3000)
"""

import base64
import time

from lxml import etree

from .base import BaseService


class XkgoService(BaseService):
    """选课系统 service"""

    PORTAL_PATH = "/portal/site/524/2412"
    XKGO_BASE = "http://xkgo.ucas.ac.cn:3000"

    async def get_selected_courses(self) -> list[dict]:
        """获取已选课程列表"""
        response = await self.portal_navigate(self.PORTAL_PATH)
        return self._parse_courses(response.text)

    def _parse_courses(self, page: str) -> list[dict]:
        """解析选课页面课程列表"""
        tree = etree.HTML(page)
        courses = []

        for row in tree.xpath("//table/tbody/tr"):
            cols = row.xpath("./td")
            if len(cols) < 8:
                continue

            course = {
                "课程编码": cols[0].xpath(".//a/text()")[0] if cols[0].xpath(".//a/text()") else "",
                "课程编码链接": cols[0].xpath(".//a/@href")[0]
                if cols[0].xpath(".//a/@href")
                else "",
                "课程名称": cols[1].xpath(".//a/text()")[0] if cols[1].xpath(".//a/text()") else "",
                "课程名称链接": cols[1].xpath(".//a/@href")[0]
                if cols[1].xpath(".//a/@href")
                else "",
                "课时": cols[2].text.strip() if cols[2].text else "",
                "学分": cols[3].text.strip() if cols[3].text else "",
                "学位课": cols[4].text.strip() if cols[4].text else "",
                "考试方式": cols[5].text.strip() if cols[5].text else "",
                "主讲教师": cols[6].xpath(".//a/text()")[0] if cols[6].xpath(".//a/text()") else "",
                "教师链接": cols[6].xpath(".//a/@href")[0] if cols[6].xpath(".//a/@href") else "",
                "跨学期课程": cols[7].text.strip() if cols[7].text else "",
            }
            courses.append(course)

        return courses

    async def search_course(self, course_code: str) -> list[dict]:
        """搜索课程"""
        api_url = f"{self.XKGO_BASE}/courseManage/selectCourse"
        data = {
            "type": "",
            "deptIds1": "&deptIds=979&deptIds=244&deptIds=245&deptIds=246&deptIds=247&deptIds=248&deptIds=249&deptIds=250&deptIds=251&deptIds=252&deptIds=253",
            "courseType1": "&courseType=1&courseType=2&courseType=3",
            "courseCode": course_code,
            "courseName": "",
        }
        response = await self.session.post(api_url, data=data)
        response.raise_for_status()
        return self._parse_search_results(response.text)

    def _parse_search_results(self, html: str) -> list[dict]:
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

    async def _get_submit_captcha(self) -> str:
        """获取并识别选课验证码"""
        timestamp = int(time.time() * 1000)
        api_url = f"{self.XKGO_BASE}/captchaImage"
        response = await self.session.get(api_url, params={"_": timestamp})
        response.raise_for_status()
        img_data = base64.b64decode(response.text.split(",")[1])
        return await self.client.captcha_handler.recognize(img_data)

    async def submit_course(self, course_id: str) -> tuple[str, str | None]:
        """提交选课"""
        captcha_code = await self._get_submit_captcha()

        api_url = f"{self.XKGO_BASE}/courseManage/saveCourse"
        data = [
            ("vcode", captcha_code),
            ("deptIds", 979),
            ("deptIds", 244),
            ("deptIds", 245),
            ("deptIds", 246),
            ("deptIds", 247),
            ("deptIds", 248),
            ("deptIds", 249),
            ("deptIds", 250),
            ("deptIds", 251),
            ("deptIds", 252),
            ("deptIds", 253),
            ("sids", course_id),
        ]
        response = await self.session.post(api_url, data=data)
        response.raise_for_status()

        return self._parse_status(response.text)

    def _parse_status(self, page: str) -> tuple[str, str | None]:
        """解析选课结果"""
        tree = etree.HTML(page)

        success = tree.xpath('//label[@id="loginSuccess"]/text()')
        if success and success[0].strip():
            return "SUCCESS", success[0].strip()

        error = tree.xpath('//label[@id="loginError"]/text()')
        if error and error[0].strip():
            return "ERROR", error[0].strip()

        return "unknown", None
