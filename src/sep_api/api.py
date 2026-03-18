"""
向后兼容 shim — uvicorn sep_api.api:app 仍然可用
"""

from .app import app  # noqa: F401
