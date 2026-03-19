"""
子系统 service 基类 — 通用 SSO 跳转 + HTML 解析
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from loguru import logger
from lxml import etree

if TYPE_CHECKING:
    import httpx

    from ..client import SEPClient


class BaseService:
    """子系统 service 基类，提供 SSO 跳转和 HTML 解析工具"""

    SEP_BASE = "https://sep.ucas.ac.cn"

    def __init__(self, client: SEPClient):
        self.client = client

    @property
    def session(self) -> httpx.AsyncClient:
        return self.client.session

    async def portal_navigate(self, portal_path: str, retries: int = 3) -> httpx.Response:
        """通用 SSO 跳转：SEP portal → 子系统

        处理两种重定向模式：
        1. JS redirect: window.location.href = '...'
        2. META REFRESH: <meta http-equiv="refresh" content="0;url=...">

        对子系统连接失败自动重试（校外网络不稳定时常见）。
        """
        last_error = None
        for attempt in range(1, retries + 1):
            try:
                url = f"{self.SEP_BASE}{portal_path}"
                response = await self.session.get(url, follow_redirects=True)
                response.raise_for_status()

                redirect_url = None

                # JS redirect
                match = re.search(r"window\.location\.href\s*=\s*'([^']+)'", response.text)
                if match:
                    redirect_url = match.group(1)

                # META REFRESH fallback
                if not redirect_url:
                    match = re.search(
                        r"<meta[^>]+http-equiv=[\"']refresh[\"'][^>]+"
                        r"content=[\"'][^\"']*url=([^\"'>\s]+)",
                        response.text,
                        re.IGNORECASE,
                    )
                    if match:
                        redirect_url = match.group(1)

                if redirect_url:
                    logger.debug(f"SSO redirect: {redirect_url}")
                    response = await self.session.get(redirect_url, follow_redirects=True)
                    response.raise_for_status()

                return response
            except Exception as e:
                last_error = e
                if attempt < retries:
                    logger.warning(f"SSO 跳转失败 (第 {attempt} 次): {e}, 重试中...")
                else:
                    logger.error(f"SSO 跳转失败 (已重试 {retries} 次): {e}")
        raise last_error  # type: ignore[misc]

    @staticmethod
    def parse_html_table(html: str, table_xpath: str = "//table") -> list[dict]:
        """通用 HTML 表格解析"""
        tree = etree.HTML(html)
        headers = tree.xpath(f"{table_xpath}/thead/tr/th/text()")
        rows = []
        for tr in tree.xpath(f"{table_xpath}/tbody/tr"):
            cells = tr.xpath("./td")
            row = {}
            for header, td in zip(headers, cells):
                text = "".join(td.xpath(".//text()")).strip()
                row[header] = text
            rows.append(row)
        return rows
