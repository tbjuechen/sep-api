"""
验证码识别模块
支持多种识别方案：Tesseract（默认）、AntiCAP、超级鹰
"""

import io
from abc import ABC, abstractmethod
from typing import Optional

from loguru import logger
from PIL import Image


class BaseCaptchaHandler(ABC):
    """验证码识别基类"""

    @abstractmethod
    async def recognize(self, image_bytes: bytes) -> str:
        """识别验证码"""
        pass


class TesseractHandler(BaseCaptchaHandler):
    """基于 Tesseract 的验证码识别（需要安装 tesseract）"""

    def __init__(self):
        try:
            import pytesseract

            self.pytesseract = pytesseract
        except ImportError:
            logger.warning("pytesseract not installed, will use fallback")
            self.pytesseract = None

    async def recognize(self, image_bytes: bytes) -> str:
        """使用 Tesseract 识别验证码"""
        if self.pytesseract is None:
            raise RuntimeError("pytesseract not available")

        img = Image.open(io.BytesIO(image_bytes))
        # 预处理：灰度化
        img = img.convert("L")
        # 二值化
        threshold = 128
        img = img.point(lambda x: 255 if x > threshold else 0)
        img = img.convert("1")

        result = self.pytesseract.image_to_string(
            img,
            config="--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
        )
        return result.strip()


class AntiCAPHandler(BaseCaptchaHandler):
    """基于 AntiCAP 的验证码识别"""

    def __init__(self):
        try:
            import AntiCAP

            self.anticap = AntiCAP
        except ImportError:
            logger.warning("AntiCAP not installed")
            self.anticap = None

    async def recognize(self, image_bytes: bytes) -> str:
        """使用 AntiCAP 识别验证码"""
        if self.anticap is None:
            raise RuntimeError("AntiCAP not available")

        import base64

        img_base64 = base64.b64encode(image_bytes).decode("utf-8")
        handler = self.anticap.Handler(show_banner=False)
        result = handler.OCR(img_base64=img_base64)
        return "".join(result)


class ChaoJiYingHandler(BaseCaptchaHandler):
    """基于超级鹰的验证码识别"""

    def __init__(self, username: str = "", password: str = "", soft_id: str = ""):
        self.username = username
        self.password = password
        self.soft_id = soft_id

    async def recognize(self, image_bytes: bytes) -> str:
        """使用超级鹰识别验证码"""
        if not self.username or not self.password:
            raise RuntimeError("Super Eagle credentials not configured")

        # TODO: 实现超级鹰 API 调用
        raise NotImplementedError("Super Eagle not implemented yet")


class CaptchaHandler:
    """验证码识别器，支持多种方案"""

    def __init__(
        self,
        method: str = "anticap",  # tesseract, anticap, chaojiying
        chaojiying_config: Optional[dict] = None,
    ):
        self.method = method
        self._handler: Optional[BaseCaptchaHandler] = None
        self._chaojiying_config = chaojiying_config or {}
        self._init_handler()

    def _init_handler(self):
        """初始化处理器"""
        if self.method == "tesseract":
            self._handler = TesseractHandler()
        elif self.method == "anticap":
            self._handler = AntiCAPHandler()
        elif self.method == "chaojiying":
            self._handler = ChaoJiYingHandler(**self._chaojiying_config)
        else:
            logger.warning(f"Unknown method {self.method}, using AntiCAP")
            self._handler = AntiCAPHandler()

    async def recognize(self, image_bytes: bytes) -> str:
        """识别验证码"""
        if self._handler is None:
            raise RuntimeError("No captcha handler available")

        try:
            return await self._handler.recognize(image_bytes)
        except Exception as e:
            logger.error(f"Captcha recognition failed: {e}")
            # 如果是 AntiCAP 失败，尝试 Tesseract
            if self.method == "anticap":
                logger.info("Falling back to Tesseract...")
                fallback = TesseractHandler()
                return await fallback.recognize(image_bytes)
            raise
