"""本地版本历史记录管理."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from gvc.config import VERSIONS_FILE
from gvc.logging_setup import get_logger

logger = get_logger()


def load_history() -> dict[str, dict[str, Any]]:
    """从 JSON 文件加载历史版本记录.

    Returns:
        {package: {version, version_code, updated_ts, last_check}, ...}
    """
    if not os.path.exists(VERSIONS_FILE):
        return {}

    try:
        with open(VERSIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 兼容旧格式：v2 中值是纯字符串
        result: dict[str, dict[str, Any]] = {}
        for k, v in data.items():
            if isinstance(v, str):
                result[k] = {"version": v}
            elif isinstance(v, dict):
                result[k] = v
        return result
    except json.JSONDecodeError as e:
        logger.warning("历史文件 JSON 解析失败: %s", e)
        return {}
    except Exception as e:
        logger.warning("读取历史文件失败: %s", e)
        return {}


def save_history(records: dict[str, dict[str, Any]]) -> None:
    """保存版本历史到 JSON 文件."""
    try:
        with open(VERSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
    except OSError as e:
        logger.error("保存历史文件失败: %s", e)


