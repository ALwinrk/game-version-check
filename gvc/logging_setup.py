"""统一日志配置."""

from __future__ import annotations

import logging
import sys

from gvc.config import LOG_LEVEL

_initialized: bool = False


def setup_logging() -> logging.Logger:
    """配置并返回 root logger."""
    global _initialized
    if _initialized:
        return logging.getLogger("gvc")

    logger = logging.getLogger("gvc")
    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        fmt = logging.Formatter(
            "%(asctime)s  %(levelname)-7s  %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(fmt)
        logger.addHandler(handler)

    _initialized = True
    return logger


def get_logger() -> logging.Logger:
    """获取 gvc logger（若未初始化则自动调用 setup_logging）."""
    return setup_logging()
