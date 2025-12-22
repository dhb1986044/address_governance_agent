"""
日志工具模块
提供统一的日志记录功能
"""
import logging
import sys
from pathlib import Path
from typing import Optional
from .config import settings


def get_logger(
    name: str,
    level: Optional[str] = None,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    获取日志记录器
    
    Args:
        name: 日志记录器名称（通常使用__name__）
        level: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
        log_file: 日志文件路径（可选）
    
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    logger = logging.getLogger(name)
    
    # 设置日志级别
    log_level = level or settings.LOG_LEVEL
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 创建格式化器
    formatter = logging.Formatter(settings.LOG_FORMAT)
    
    # 添加控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 添加文件处理器（如果指定）
    file_path = log_file or settings.LOG_FILE
    if file_path:
        log_path = Path(file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


if __name__ == "__main__":
    """测试日志功能"""
    logger = get_logger(__name__, level="DEBUG")
    
    logger.debug("这是一条DEBUG级别日志")
    logger.info("这是一条INFO级别日志")
    logger.warning("这是一条WARNING级别日志")
    logger.error("这是一条ERROR级别日志")
    logger.critical("这是一条CRITICAL级别日志")
