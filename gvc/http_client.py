"""HTTP 客户端 — 会话管理、重试、UA 轮换、Cloudflare 检测."""

from __future__ import annotations

import random
import time

import requests

from gvc.config import CF_TIMEOUT, MAX_RETRIES, REQUEST_TIMEOUT, RETRY_BACKOFF, get_proxies
from gvc.logging_setup import get_logger

try:
    from curl_cffi import requests as cf_requests
except ImportError:
    cf_requests = None

logger = get_logger()

# ── Cloudflare 检测 ──────────────────────────────────────

_CF_SIGNATURES: list[str] = [
    "cf-browser-verify",
    "Cloudflare",
    "Attention Required",
    "cf-challenge",
    "cf_captcha",
    "cf-wrapper",
    "Checking your browser",
    "DDoS protection",
    "Just a moment",
]


def is_cloudflare_block(html: str) -> bool:
    """检测是否为 Cloudflare JS 挑战页面.

    Cloudflare 的 JS 挑战即使是 curl_cffi 模拟 Chrome 也无法绕过，
    检测到后应直接判定为不可达，避免浪费重试时间。

    Args:
        html: HTTP 响应正文.

    Returns:
        True 如果检测到 Cloudflare 拦截特征.
    """
    if len(html) > 20000:  # 正常页面一般 > 20KB
        return False
    html_lower = html.lower()
    return any(sig.lower() in html_lower for sig in _CF_SIGNATURES)

_USER_AGENTS: list[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

_regular_session: requests.Session | None = None


def _init_session() -> requests.Session:
    global _regular_session
    if _regular_session is None:
        _regular_session = requests.Session()
        _regular_session.headers.update({
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
    _regular_session.headers["User-Agent"] = random.choice(_USER_AGENTS)
    return _regular_session


def _classify_http_error(status: int) -> str:
    if status in (404, 410):
        return "retryable"
    if 400 <= status < 500:
        return "fatal"
    if status >= 500:
        return "retryable"
    return "fatal"


def _can_connect(host: str, port: int = 443, timeout: float = 2.0) -> bool:
    """快速检测 TCP 是否可达."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False


def http_get(url: str) -> tuple[int, str]:
    """GET 请求，带重试和 curl_cffi 降级.

    优化：TCP 不通时跳过 requests 直接走 curl_cffi，减少等待时间。
    """
    from urllib.parse import urlparse
    host = urlparse(url).hostname or ""
    last_error = ""
    proxies = get_proxies()

    # ── 阶段 1：requests + 重试 ──
    # TCP 预检：无代理时如果 TCP 不通，直接跳过 requests
    skip_requests = not proxies and host and not _can_connect(host)
    if skip_requests:
        last_error = f"TCP blocked: {host}"
    else:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                session = _init_session()
                resp = session.get(url, timeout=REQUEST_TIMEOUT, proxies=proxies)
                if resp.status_code == 200 and len(resp.text) > 500:
                    return resp.status_code, resp.text
                if resp.status_code == 403:
                    last_error = f"HTTP 403 (attempt {attempt})"
                    # 不在此处判定 CF，留给 curl_cffi 阶段尝试（模拟 Chrome 可能绕过）
                    break
                classification = _classify_http_error(resp.status_code)
                if classification == "fatal":
                    return resp.status_code, resp.text
                last_error = f"HTTP {resp.status_code} (attempt {attempt})"
            except requests.ConnectionError:
                last_error = f"ConnectionError: {url[:60]}"
            except requests.Timeout:
                last_error = f"Timeout: {url[:60]}"
            except requests.RequestException as e:
                last_error = f"RequestException: {e!s}"[:80]

            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF ** attempt)

    # ── 阶段 2：curl_cffi 降级 ──
    if cf_requests is not None:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                cf_proxies = proxies if proxies else {}
                resp = cf_requests.get(url, impersonate="chrome124", timeout=CF_TIMEOUT, proxies=cf_proxies)
                if resp.status_code == 200 and len(resp.text) > 500:
                    logger.debug("curl_cffi success on %s", url[:60])
                    return resp.status_code, resp.text
                # Cloudflare JS 挑战 — 即使 curl_cffi 模拟 Chrome 也无法绕过
                if resp.status_code == 403 and is_cloudflare_block(resp.text):
                    return 0, f"Cloudflare blocked: {host}"
                classification = _classify_http_error(resp.status_code)
                if classification == "fatal":
                    return resp.status_code, resp.text
                last_error = f"cf HTTP {resp.status_code}"
            except Exception as e:
                last_error = f"cf error: {e!s}"[:80]

            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF ** attempt)
    else:
        last_error = "curl_cffi not installed"

    logger.warning("All attempts failed for %s: %s", url[:60], last_error)
    return 0, last_error


# 向后兼容别名
_http_get = http_get
