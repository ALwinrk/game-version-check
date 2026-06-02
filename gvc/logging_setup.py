"""统一日志配置."""

from __future__ import annotations

import logging
import sys

from gvc.config import LOG_LEVEL

_initialized: bool = False


def _make_utf8_stream_handler() -> logging.StreamHandler:
    """创建支持 UTF-8 输出的 StreamHandler, 兼容 Windows GBK 终端和 PyInstaller GUI 模式."""
    # PyInstaller GUI 模式 (console=False) 时 sys.stdout 为 None
    stream = sys.stdout or sys.stderr
    if stream is None:
        # 完全没有控制台 — 写入文件
        return logging.FileHandler("gvc_debug.log", encoding="utf-8")

    if sys.platform == "win32" and hasattr(stream, "buffer"):
        import io
        utf8_stream = io.TextIOWrapper(
            stream.buffer,
            encoding="utf-8",
            errors="replace",
        )
        return logging.StreamHandler(utf8_stream)
    return logging.StreamHandler(stream)


def setup_logging() -> logging.Logger:
    """配置并返回 root logger."""
    global _initialized
    if _initialized:
        return logging.getLogger("gvc")

    logger = logging.getLogger("gvc")
    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))

    if not logger.handlers:
        handler = _make_utf8_stream_handler()
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
