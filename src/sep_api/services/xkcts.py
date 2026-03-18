
"""
教务子系统 service (xkcts.ucas.ac.cn:8443)
包含成绩查询、讲座查询等功能
"""

import asyncio
from typing import List, Dict, Any
from lxml import etree
from .base import BaseService

class XkctsService(BaseService):
    """教务系统 service"""

    PORTAL_PATH = "/portal/site/226/821"
    XKCTS_BASE = "https://xkcts.ucas.ac.cn:8443"

    async def get_grades(self) -> List[Dict[str, Any]]:
        """获取所有成绩"""
        # 确保已登录并建立 session
        await self.portal_navigate(self.PORTAL_PATH)
        
        # 直接访问所有成绩页面
        api_url = f"{self.XKCTS_BASE}/score/yjs/all"
        response = await self.session.get(api_url)
        response.raise_for_status()
        
        return self._parse_grades(response.text)

    def _parse_grades(self, html: str) -> List[Dict[str, Any]]:
        """解析成绩页面"""
        tree = etree.HTML(html)
        table = tree.xpath("//table[contains(@class, 'table-striped')]")
        if not table:
            return []
        
        table = table[0]
        headers = table.xpath(".//thead/tr/th/text()")
        headers = [h.strip() for h in headers]
        
        grades = []
        for tr in table.xpath(".//tbody/tr"):
            cells = tr.xpath("./td")
            row = {}
            for header, td in zip(headers, cells):
                text = "".join(td.xpath(".//text()")).strip()
                row[header] = text
            if row:
                grades.append(row)
        return grades

    async def get_lectures_humanity_record(self) -> List[Dict[str, Any]]:
        """获取人文讲座报名及听课记录"""
        await self.portal_navigate(self.PORTAL_PATH)
        
        api_url = f"{self.XKCTS_BASE}/subject/humanityStudent"
        response = await self.session.get(api_url)
        response.raise_for_status()
        
        return self._parse_lectures(response.text)

    async def get_lectures_science_record(self) -> List[Dict[str, Any]]:
        """获取科学前沿讲座听讲情况"""
        await self.portal_navigate(self.PORTAL_PATH)
        
        api_url = f"{self.XKCTS_BASE}/subject/student"
        response = await self.session.get(api_url)
        response.raise_for_status()
        
        return self._parse_lectures(response.text)

    async def get_lectures_humanity_list(self) -> List[Dict[str, Any]]:
        """获取人文讲座预告（报名）列表"""
        await self.portal_navigate(self.PORTAL_PATH)
        
        api_url = f"{self.XKCTS_BASE}/subject/humanityLecture"
        response = await self.session.get(api_url)
        response.raise_for_status()
        
        lectures = self._parse_lectures(response.text)
        
        # 如果列表中主讲人为空，并发去详情页抓取
        tasks = []
        for lec in lectures:
            if (not lec.get("主讲人") or lec.get("主讲人") == "") and lec.get("详情链接"):
                tasks.append(self._fill_speaker(lec))
        
        if tasks:
            await asyncio.gather(*tasks)
            
        return lectures

    async def _fill_speaker(self, lecture: dict) -> None:
        """从详情页抓取主讲人并填充到字典"""
        detail_path = lecture.get("详情链接")
        if not detail_path:
            return
            
        try:
            url = f"{self.XKCTS_BASE}{detail_path}"
            response = await self.session.get(url)
            if response.status_code == 200:
                tree = etree.HTML(response.text)
                # 尝试查找包含"主讲人"文字的表格单元格
                # 通常是 "主讲人：XXX" 这种格式
                td_text = "".join(tree.xpath("//td[contains(text(), '主讲人')]/text()")).strip()
                if td_text:
                    import re
                    match = re.search(r"主讲人[：:]([^，,。;\s]+)", td_text)
                    if match:
                        lecture["主讲人"] = match.group(1).strip()
                    else:
                        # 如果正则没匹配到，就取前几个字，或者整行
                        lecture["主讲人"] = td_text.split("：")[1].split("，")[0].strip() if "：" in td_text else td_text
        except Exception:
            # 抓取失败不影响列表展示，保持为空即可
            pass

    async def get_evaluation_list(self) -> List[Dict[str, Any]]:
        """获取评估课程列表"""
        await self.portal_navigate(self.PORTAL_PATH)
        
        # 查找评估链接
        response = await self.session.get(f"{self.XKCTS_BASE}/notice/view/1")
        tree = etree.HTML(response.text)
        eval_links = tree.xpath("//a[contains(@href, '/evaluate/course/')]/@href")
        if not eval_links:
            return []
            
        # 进入评估列表页面
        eval_url = f"{self.XKCTS_BASE}{eval_links[0]}"
        response = await self.session.get(eval_url)
        response.raise_for_status()
        
        tree = etree.HTML(response.text)
        rows = tree.xpath("//table[contains(@class, 'table')]/tbody/tr")
        eval_list = []
        for row in rows:
            cols = row.xpath("./td")
            if len(cols) < 8: continue
            
            status = "".join(cols[7].xpath(".//text()")).strip()
            # 状态如果是按钮，文字可能在里面
            if not status:
                status = "".join(cols[7].xpath(".//a/text()")).strip()
                
            course = {
                "课程编码": "".join(cols[0].xpath(".//text()")).strip(),
                "课程名称": "".join(cols[1].xpath(".//text()")).strip(),
                "课时": "".join(cols[2].xpath(".//text()")).strip(),
                "学分": "".join(cols[3].xpath(".//text()")).strip(),
                "学位课": "".join(cols[4].xpath(".//text()")).strip(),
                "考试方式": "".join(cols[5].xpath(".//text()")).strip(),
                "主讲教师": "".join(cols[6].xpath(".//text()")).strip(),
                "状态": status or "已评估",
                "评估链接": cols[7].xpath(".//a/@href")[0] if cols[7].xpath(".//a/@href") else None
            }
            eval_list.append(course)
        return eval_list

    async def auto_evaluate_course(self, eval_path: str) -> tuple[bool, str]:
        """自动评估课程（全优）"""
        if not eval_path: return False, "Invalid eval path"
        
        # 1. 获取表单
        url = f"{self.XKCTS_BASE}{eval_path}"
        response = await self.session.get(url)
        response.raise_for_status()
        
        tree = etree.HTML(response.text)
        form = tree.xpath("//form[@id='evaluateForm']")
        if not form:
            form = tree.xpath("//form")
        if not form:
            return False, "Evaluation form not found"
            
        action = form[0].get("action")
        
        # 2. 准备数据
        data = {}
        
        # Radio 分组全选最高分 (通常是 5)
        radios = form[0].xpath(".//input[@type='radio']")
        groups = set([r.get('name') for r in radios if r.get('name')])
        for group in groups:
            # 获取该组的所有可选值，取最大的那个 (通常 5 是优)
            values = form[0].xpath(f".//input[@name='{group}']/@value")
            if values:
                data[group] = max(values, key=lambda x: int(x) if x.isdigit() else 0)
        
        # Textarea 填默认好评
        textareas = form[0].xpath(".//textarea")
        for ta in textareas:
            name = ta.get("name")
            if name:
                data[name] = "非常满意的课程，老师讲解清晰，收获很大。"
                
        # 3. 提交
        submit_url = f"{self.XKCTS_BASE}{action}"
        response = await self.session.post(submit_url, data=data)
        
        if response.status_code in [200, 302]:
            return True, "评估提交成功"
        else:
            return False, f"提交失败 (Status: {response.status_code})"

    def _parse_lectures(self, html: str) -> List[Dict[str, Any]]:
        """解析讲座相关表格"""
        tree = etree.HTML(html)
        table = tree.xpath("//table[contains(@class, 'table-striped')]")
        if not table:
            return []
        
        table = table[0]
        headers = table.xpath(".//thead/tr/th/text()")
        headers = [h.strip() for h in headers]
        
        lectures = []
        for tr in table.xpath(".//tbody/tr"):
            cells = tr.xpath("./td")
            if not cells:
                continue
            row = {}
            for header, td in zip(headers, cells):
                # 处理 checkbox (是否有效)
                checkbox = td.xpath(".//input[@type='checkbox']")
                if checkbox:
                    is_checked = checkbox[0].get("checked") == "checked"
                    row[header] = "有效" if is_checked else "无效"
                else:
                    text = "".join(td.xpath(".//text()")).strip()
                    row[header] = text
                
                # 特殊处理：如果列头是'操作区'，尝试提取查看详情的链接
                if header == "操作区":
                    link = td.xpath(".//a[contains(@href, 'View')]/@href")
                    if link:
                        row["详情链接"] = link[0]

            if row:
                lectures.append(row)
        return lectures
