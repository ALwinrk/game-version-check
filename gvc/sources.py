"""6 个数据源的并发查询 — Google Play 为主，APK 站点为辅."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from typing import Callable

from gvc.config import MAX_SOURCE_WORKERS, get_proxies
from gvc.http_client import http_get, is_cloudflare_block
from gvc.logging_setup import get_logger
from gvc.models import SourceResult
from gvc.parser import extract_version, extract_version_code

logger = get_logger()


# ── Google Play ──────────────────────────────────────────


def _setup_urllib_proxy() -> None:
    """确保 urllib 能通过代理访问 Google Play.

    google-play-scraper 底层使用 urllib.request.urlopen()，
    它通过 getproxies() 读取 HTTP_PROXY / HTTPS_PROXY 环境变量。
    本函数从项目配置中读取代理并注入到环境变量。
    """
    proxies = get_proxies()
    if not proxies:
        return
    for scheme_key, env_key in [("http", "HTTP_PROXY"), ("https", "HTTPS_PROXY")]:
        if scheme_key in proxies:
            os.environ[env_key] = proxies[scheme_key]
            # urllib 在某些平台上优先检查小写变量名
            os.environ[env_key.lower()] = proxies[scheme_key]


def check_google(package: str) -> SourceResult:
    """通过 google-play-scraper 查询 Google Play（最权威来源）.

    Google Play 通常是全球最先发布更新的渠道，作为优先数据源。
    需要代理（Clash 7897）才能从中国大陆访问。
    """
    try:
        _setup_urllib_proxy()
        from google_play_scraper import app as gp_app

        info = gp_app(package, lang="en", country="us")
        version = info.get("version", "")
        updated = info.get("updated")
        if version.lower() in ("varies with device", "varies", ""):
            return SourceResult(error="Varies with device")
        logger.debug("Google Play %s → %s", package, version)
        return SourceResult(version=version, updated_ts=updated)
    except ImportError:
        return SourceResult(error="google-play-scraper not installed")
    except Exception as e:
        err_msg = f"{type(e).__name__}: {e!s}"[:100]
        # 检测常见错误并给出友好提示
        if "404" in err_msg or "NotFoundError" in err_msg:
            err_msg = "App not found on Google Play"
        elif "URLError" in err_msg or "timeout" in err_msg.lower():
            err_msg = "Google Play unreachable (proxy needed)"
        return SourceResult(error=err_msg)


# ── APK 站点 ─────────────────────────────────────────────


def _check_apk_site(url: str) -> SourceResult:
    """通用 APK 站点查询 — 带 Cloudflare 快速判定."""
    try:
        status, html = http_get(url)
        if status != 200:
            return SourceResult(
                error=f"HTTP {status}" if status else f"连接失败: {html[:40]}"
            )
        if is_cloudflare_block(html):
            return SourceResult(error="Cloudflare 拦截 (JS Challenge)")
        version = extract_version(html)
        vcode = extract_version_code(html)
        if version:
            return SourceResult(version=version, version_code=vcode)
        return SourceResult(version_code=vcode, error=f"未匹配版本 ({len(html)} 字节)")
    except Exception as e:
        return SourceResult(error=f"{type(e).__name__}: {e!s}"[:80])


def check_apkpure(pkg: str) -> SourceResult:
    # .com 有完整数据但需代理；.net 是 Lite 版仅作兜底
    result = _check_apk_site(f"https://apkpure.com/search?q={pkg}")
    if result.version:
        return result
    return _check_apk_site(f"https://apkpure.net/search?q={pkg}")


def check_apkcombo(pkg: str) -> SourceResult:
    # .com 需代理，.cc 已废（TCP 可通但始终返回 500）
    return _check_apk_site(f"https://apkcombo.com/search?q={pkg}")


def check_apkvision(pkg: str) -> SourceResult:
    """APKVision — TCP 可通但被 Cloudflare JS Challenge 拦截 (永久 403)."""
    return _check_apk_site(f"https://apkvision.org/search?q={pkg}")


def check_apkmirror(pkg: str) -> SourceResult:
    """APKMirror — TCP 被 GFW 封锁，且被 Cloudflare JS Challenge 拦截.

    即使配置代理也无法绕过 Cloudflare 的 JS 挑战。
    """
    return _check_apk_site(f"https://www.apkmirror.com/?s={pkg}")


def check_apkdl(pkg: str) -> SourceResult:
    """APKDL — TCP 可通但页面由 JS 动态渲染，无法提取静态版本数据."""
    return _check_apk_site(f"https://apkdl.com/search?q={pkg}")


# ── 站点评测器注册表 ─────────────────────────────────────

CheckerFunc = Callable[[str], SourceResult]

# 有效来源（2026-05）:
#   Google Play ✓ 最权威，需代理，google-play-scraper
#   APKPure     ✓ 需代理，.com 完整数据 / .net 仅兜底
#   APKCombo    ✓ 需代理，.com 正常（.cc 已废）
#
# 已移除的不可用来源:
#   APKVision   ✗ Cloudflare JS Challenge 永久拦截
#   APKMirror   ✗ GFW TCP 封锁 + Cloudflare JS Challenge
#   APKDL       ✗ JS 动态渲染，无法静态提取版本
CHECKERS: list[tuple[str, CheckerFunc]] = [
    ("Google Play", check_google),
    ("APKPure", check_apkpure),
    ("APKCombo", check_apkcombo),
]


# ── 并发查询入口 ─────────────────────────────────────────


def query_all_sources(package: str) -> dict[str, SourceResult]:
    """并发查询所有数据源.

    Args:
        package: Android 包名.

    Returns:
        {source_name: SourceResult} 字典.
    """
    results: dict[str, SourceResult] = {}
    with ThreadPoolExecutor(max_workers=min(len(CHECKERS), MAX_SOURCE_WORKERS)) as executor:
        future_map: dict[Future, str] = {
            executor.submit(fn, package): name
            for name, fn in CHECKERS
        }
        for future in as_completed(future_map):
            name = future_map[future]
            try:
                results[name] = future.result()
            except Exception as e:
                logger.warning("%s 查询异常: %s", name, e)
                results[name] = SourceResult(error=f"{type(e).__name__}: {e!s}"[:100])
    return results
