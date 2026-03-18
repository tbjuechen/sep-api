"""
共享依赖 — 会话管理
"""

from fastapi import HTTPException

from .client import SEPClient

_sessions: dict[str, SEPClient] = {}


def get_client(session_id: str) -> SEPClient:
    """获取客户端实例"""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found, please login first")
    return _sessions[session_id]
