"""
核心基础设施层 - 无外部依赖
提供配置管理、日志、API客户端等基础服务
"""

from .config import settings
from .logger import get_logger
from .fengtu_client import FengtuClient

__all__ = ["settings", "get_logger", "FengtuClient"]
