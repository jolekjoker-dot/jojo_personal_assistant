"""
日志系统 — 基于 loguru，支持彩色控制台输出和文件轮转。
"""

import sys
from pathlib import Path

from loguru import logger as _logger

from src.jojo.config import config


def setup_logger() -> None:
    """初始化日志配置。"""
    # 移除默认 handler
    _logger.remove()

    # 控制台输出 — 彩色格式
    _logger.add(
        sys.stderr,
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        level=config.log_level,
        colorize=True,
    )

    # 文件输出 — 按天轮转
    log_path = Path(config.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    _logger.add(
        log_path,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
               "{name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="10 MB",
        retention="7 days",
        encoding="utf-8",
    )


# 模块级 logger 实例
logger = _logger
