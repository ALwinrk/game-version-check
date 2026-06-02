"""HTTP 客户端 — 基于 Scrapling 的双层后端: FetcherSession (快) + StealthySession (CF 绕过)."""

from __future__ import annotations

import threading
from urllib.parse import urlparse

from gvc.config import REQUEST_TIMEOUT, MAX_RETRIES, RETRY_BACKOFF, STEALTH_TIMEOUT, get_proxies
from gvc.logging_setup import get_logger

# Scrapling fetchers (依赖 scrapling[fetchers])
from scrapling import Fetcher
from scrapling.fetchers import StealthySession  # noqa: F401 (used in stealth_get)

logger = get_logger()

# ── Cloudflare 检测 (兜底) ────────────────────────────────

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

    StealthySession.solve_cloudflare=True 通常会自动处理,
    但某些边缘情况可能失败, 此函数作为兜底检测.

    Args:
        html: HTTP 响应正文.

    Returns:
        True 如果检测到 Cloudflare 拦截特征.
    """
    if len(html) > 20000:  # 正常页面一般 > 20KB
        return False
    html_lower = html.lower()
    return any(sig.lower() in html_lower for sig in _CF_SIGNATURES)


# ── 快速后端: Fetcher (curl_cffi + browserforge) ─────────

_fetcher: Fetcher | None = None
_fetcher_lock = threading.Lock()


def get_fetcher() -> Fetcher:
    """获取或创建持久化 Fetcher 实例.

    Fetcher 基于 curl_cffi, 自动使用 browserforge 生成
    真实浏览器头部. 线程安全 (curl_cffi 底层).
    """
    global _fetcher
    if _fetcher is None:
        with _fetcher_lock:
            if _fetcher is None:
                _fetcher = Fetcher()
    return _fetcher


def http_get(url: str) -> tuple[int, str]:
    """快速 HTTP GET — 通过 Scrapling Fetcher (curl_cffi + browserforge).

    替代原有的 requests → curl_cffi 双阶段架构.
    内置 browserforge 头部生成 + 自动重试 + 代理支持.

    Args:
        url: 目标 URL.

    Returns:
        (status_code, html) 元组. status_code 为 0 表示连接失败.
    """
    proxies = get_proxies()
    try:
        fetcher = get_fetcher()
        resp = fetcher.get(
            url,
            timeout=int(REQUEST_TIMEOUT),
            retries=MAX_RETRIES,
            retry_delay=RETRY_BACKOFF,
            impersonate="chrome124",
            stealthy_headers=True,
            proxies=proxies if proxies else None,
        )
        if resp.status == 200 and len(resp.html_content) > 500:
            return resp.status, resp.html_content
        # 非 200 或响应体太短
        if resp.status == 403 and is_cloudflare_block(resp.html_content):
            return 0, f"Cloudflare blocked: {urlparse(url).hostname}"
        return resp.status, resp.html_content or ""
    except Exception as e:
        logger.exception("Fetcher failed for %s: %s", url[:60], e)
        return 0, f"{type(e).__name__}: {e!s}"[:80]


# ── 隐身后端: StealthySession (Chromium + CF 绕过) ──────────

_stealthy_lock = threading.Lock()


def stealth_get(url: str, *, use_proxy: bool = False) -> tuple[int, str]:
    """浏览器 GET — 用于 Cloudflare 保护的站点.

    通过 Chromium 无头浏览器访问, 自动解决 CF JS Challenge.
    比 http_get 慢得多 (~5-10s/页, 含浏览器启动).

    Args:
        url: 目标 URL.
        use_proxy: 是否配置代理。APKMirror 需要 (GFW TCP 封锁);
                   APKVision/APKDL 在国内 TCP 可达, 不需要代理。

    Returns:
        (status_code, html) 元组.
    """
    with _stealthy_lock:
        try:
            proxy_config = None
            if use_proxy:
                proxies = get_proxies()
                if proxies:
                    proxy_url = proxies.get("https") or proxies.get("http")
                    if proxy_url:
                        proxy_config = {"server": proxy_url}

            from gvc import get_chromium_executable
            chrome_exe = get_chromium_executable()

            with StealthySession(
                headless=True,
                solve_cloudflare=True,
                block_ads=True,
                disable_resources=True,
                timeout=int(STEALTH_TIMEOUT * 1000),
                google_search=False,
                proxy=proxy_config,
                executable_path=chrome_exe,
            ) as s:
                resp = s.fetch(url)
                if resp.status == 200 and len(resp.html_content) > 500:
                    if is_cloudflare_block(resp.html_content):
                        return 0, f"Cloudflare bypass failed: {urlparse(url).hostname}"
                    return resp.status, resp.html_content
                return resp.status, resp.html_content or ""
        except Exception as e:
            logger.exception("StealthySession failed for %s: %s", url[:60], e)
            return 0, f"{type(e).__name__}: {e!s}"[:80]


def reset_sessions() -> None:
    """重置所有持久化会话 (用于长时间运行后的内存清理)."""
    global _fetcher
    with _fetcher_lock:
        if _fetcher:
            try:
                _fetcher.close()
            except Exception:
                pass
            _fetcher = None
