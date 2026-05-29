"""全局配置 — 可通过环境变量覆盖."""

from __future__ import annotations

import os


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


# ── 并发 & 速率 ──────────────────────────────────────────
MAX_GAME_WORKERS: int = _env_int("GVC_MAX_GAME_WORKERS", 3)
MAX_SOURCE_WORKERS: int = _env_int("GVC_MAX_SOURCE_WORKERS", 5)

# ── HTTP ─────────────────────────────────────────────────
REQUEST_TIMEOUT: float = _env_float("GVC_REQUEST_TIMEOUT", 10.0)
CF_TIMEOUT: float = _env_float("GVC_CF_TIMEOUT", 12.0)
MAX_RETRIES: int = _env_int("GVC_MAX_RETRIES", 3)
RETRY_BACKOFF: float = _env_float("GVC_RETRY_BACKOFF", 1.5)

# ── Excel 列位置 ─────────────────────────────────────────
COL_NAME: int = _env_int("GVC_COL_NAME", 1)
COL_PACKAGE: int = _env_int("GVC_COL_PACKAGE", 2)
COL_CURRENT: int = _env_int("GVC_COL_CURRENT", 3)
COL_CURRENT_VC: int = _env_int("GVC_COL_CURRENT_VC", 4)

# ── 本地历史 ─────────────────────────────────────────────
VERSIONS_FILE: str = os.environ.get("GVC_VERSIONS_FILE", "last_versions.json")

# ── 日志 ─────────────────────────────────────────────────
LOG_LEVEL: str = os.environ.get("GVC_LOG_LEVEL", "INFO")

# ── 代理 ─────────────────────────────────────────────────
# 注意：代理值每次调用 get_proxies() 时实时读取，方便 GUI 运行时修改


def get_proxies() -> dict | None:
    """返回 requests 库格式的代理字典，未配置则返回 None.

    每次调用都重新读取环境变量，支持运行时动态修改代理设置。
    优先使用 GVC_HTTP_PROXY / GVC_HTTPS_PROXY，回退到标准 HTTP_PROXY / HTTPS_PROXY。
    """
    http_p = os.environ.get("GVC_HTTP_PROXY") or os.environ.get("HTTP_PROXY", "")
    https_p = os.environ.get("GVC_HTTPS_PROXY") or os.environ.get("HTTPS_PROXY", "")
    proxies = {}
    if http_p:
        proxies["http"] = http_p
    if https_p:
        proxies["https"] = https_p
    return proxies if proxies else None
