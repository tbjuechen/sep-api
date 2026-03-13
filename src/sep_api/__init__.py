"""
国科大教务系统 API 中转站
"""

__version__ = "0.1.0"

from .client import SEPClient

__all__ = ["SEPClient", "__version__"]