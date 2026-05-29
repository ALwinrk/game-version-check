"""5 个数据源的并发查询."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from typing import Callable

from gvc.config import MAX_SOURCE_WORKERS
from gvc.http_client import http_get
from gvc.logging_setup import get_logger
from gvc.models import SourceResult
from gvc.parser import extract_version, extract_version_code

logger = get_logger()

# ── Google Play ──────────────────────────────────────────


def check_google(package: str) -> SourceResult:
    """通过 google-play-scraper 查询 Google Play."""
    try:
        from google_play_scraper import app as gp_app

        info = gp_app(package, lang="en", country="us")
        version = info.get("version", "")
        updated = info.get("updated")
        if version.lower() in ("varies with device", "varies", ""):
            return SourceResult(error="Varies with device")
        return SourceResult(version=version, updated_ts=updated)
    except ImportError:
        return SourceResult(error="google-play-scraper not installed")
    except Exception as e:
        return SourceResult(error=f"{type(e).__name__}: {e!s}"[:100])


# ── APK 站点 ─────────────────────────────────────────────


def _check_apk_site(url: str) -> SourceResult:
    """通用 APK 站点查询."""
    try:
        status, html = http_get(url)
        if status != 200:
            return SourceResult(
                error=f"HTTP {status}" if status else f"连接失败: {html[:40]}"
            )
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
    # apkcombo.cc 在中国大陆 TCP 可通，优先使用
    result = _check_apk_site(f"https://apkcombo.cc/search?q={pkg}")
    if result.version:
        return result
    # 回退到 .com（代理用户可用）
    return _check_apk_site(f"https://apkcombo.com/search?q={pkg}")


def check_apkvision(pkg: str) -> SourceResult:
    return _check_apk_site(f"https://apkvision.org/search?q={pkg}")


def check_apkmirror(pkg: str) -> SourceResult:
    return _check_apk_site(f"https://www.apkmirror.com/?s={pkg}")


def check_apkdl(pkg: str) -> SourceResult:
    """APKDL — 在中国大陆可直连访问的 APK 信息站."""
    return _check_apk_site(f"https://apkdl.com/search?q={pkg}")


# ── 站点评测器注册表 ─────────────────────────────────────

CheckerFunc = Callable[[str], SourceResult]

CHECKERS: list[tuple[str, CheckerFunc]] = [
    ("Google Play", check_google),
    ("APKPure", check_apkpure),
    ("APKCombo", check_apkcombo),
    ("APKVision", check_apkvision),
    ("APKMirror", check_apkmirror),
    ("APKDL", check_apkdl),
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
