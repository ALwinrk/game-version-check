"""6 个数据源的并发查询 — 快/慢两级, 支持 Scrapling Fetcher + Stealthy 双后端."""

from __future__ import annotations

import os
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from typing import Callable
from urllib.parse import urljoin, urlparse

from gvc.config import MAX_SOURCE_WORKERS, MAX_GAME_WORKERS, get_proxies
from gvc.http_client import http_get, stealth_get, is_cloudflare_block
from gvc.logging_setup import get_logger
from gvc.models import SourceResult
from gvc.parser import extract_version, extract_version_code, extract_both

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
    Google Play 不能直接下载 APK，detail_url 留空。
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
        return SourceResult(
            version=version,
            updated_ts=updated,
            detail_url=f"https://play.google.com/store/apps/details?id={package}",
        )
    except ImportError:
        return SourceResult(error="google-play-scraper not installed")
    except Exception as e:
        err_msg = f"{type(e).__name__}: {e!s}"[:100]
        if "404" in err_msg or "NotFoundError" in err_msg:
            err_msg = "App not found on Google Play"
        elif "URLError" in err_msg or "timeout" in err_msg.lower():
            err_msg = "Google Play unreachable (proxy needed)"
        return SourceResult(error=err_msg)


# ── 快速 APK 站点 (FetcherSession) ──────────────────────


def _extract_detail_url(html: str, base_url: str) -> str | None:
    """从搜索结果页提取第一个结果的详情页链接.

    各站点结构不同，用多个策略尝试。
    """
    host = urlparse(base_url).hostname or ""

    # APKPure: /package-name.html 或 /app/...
    if "apkpure" in host:
        # 搜索页结果通常是 <a href="/pkg.html">
        m = re.search(r'href="/([^"]+?(?:download|/)[^"]*)"', html)
        if m:
            return urljoin(base_url, m.group(1))
        # 备用：任意 /package-name 链接
        m = re.search(r'href="(/[a-z][a-z0-9._-]+\.html)"', html)
        if m:
            return urljoin(base_url, m.group(1))

    # APKCombo: /package-name/download 或 /package-name/
    if "apkcombo" in host:
        m = re.search(r'href="(/(?:[a-z]{2}/)?[^"]+?/download[^"]*)"', html)
        if m:
            return urljoin(base_url, m.group(1))
        m = re.search(r'href="(/[a-z]{2}/[^"]+?/[^"]+/)"', html)
        if m:
            return urljoin(base_url, m.group(1))

    # 通用兜底：找第一个看起来像详情页的链接
    m = re.search(r'href="((?:/[a-z]{2})?/[^"]*?(?:download|apk|app)[^"]*)"', html, re.IGNORECASE)
    if m:
        return urljoin(base_url, m.group(1))

    return None


def _check_apk_site(url: str) -> SourceResult:
    """快速源通用查询 — 通过 FetcherSession 获取并提取版本信息."""
    try:
        status, html = http_get(url)
        if status != 200:
            return SourceResult(
                error=f"HTTP {status}" if status else f"连接失败: {html[:40]}"
            )
        if is_cloudflare_block(html):
            return SourceResult(error="Cloudflare 拦截 (JS Challenge)")
        version, vcode = extract_both(html)
        detail_url = _extract_detail_url(html, url)
        if version:
            return SourceResult(version=version, version_code=vcode, detail_url=detail_url)
        return SourceResult(
            version_code=vcode,
            detail_url=detail_url,
            error=f"未匹配版本 ({len(html)} 字节)",
        )
    except Exception as e:
        return SourceResult(error=f"{type(e).__name__}: {e!s}"[:80])


def check_apkpure(pkg: str) -> SourceResult:
    """APKPure — 快速源, FetcherSession.

    .com 有完整数据但需代理；.net 是 Lite 版仅作兜底。
    永久性阻断（CF/403）时跳过 .net 回退。
    """
    result = _check_apk_site(f"https://apkpure.com/search?q={pkg}")
    if result.version:
        return result
    # 永久性阻断不回退（.net 同机房同样被拦）
    if result.error and any(
        kw in (result.error or "").lower()
        for kw in ("cloudflare", "403", "tcp block", "js challenge")
    ):
        return result
    return _check_apk_site(f"https://apkpure.net/search?q={pkg}")


def check_apkcombo(pkg: str) -> SourceResult:
    """APKCombo — 快速源, FetcherSession.

    .com 需代理，.cc 已废（TCP 可通但始终返回 500）。
    """
    return _check_apk_site(f"https://apkcombo.com/search?q={pkg}")


# ── 慢速 APK 站点 (StealthySession, 浏览器 + CF 绕过) ────


def _extract_detail_url_stealth(html: str, base_url: str) -> str | None:
    """从浏览器渲染后的搜索结果页提取详情页链接.

    慢速源（APKVision/APKMirror/APKDL）页面可能被 CF 保护或 JS 渲染，
    链接结构不同。
    """
    host = urlparse(base_url).hostname or ""

    if "apkmirror" in host:
        # APKMirror 搜索结果为 /apk/{publisher}/{app}/ 格式
        m = re.search(r'href="(/apk/[^"]+/[^"]+/)"', html)
        if m:
            return urljoin(base_url, m.group(1))

    if "apkvision" in host:
        # APKVision: /app/... 或 /download/...
        m = re.search(r'href="(/[^"]*?(?:app|download|game)[^"]*/)"', html, re.IGNORECASE)
        if m:
            return urljoin(base_url, m.group(1))

    if "apkdl" in host:
        # APKDL: /download/... 或 /app/...
        m = re.search(r'href="(/[^"]*?(?:download|app)[^"]*\.html)"', html)
        if m:
            return urljoin(base_url, m.group(1))
        m = re.search(r'href="(/[a-z][a-z0-9._-]+/)"', html)
        if m:
            return urljoin(base_url, m.group(1))

    # 通用兜底
    return _extract_detail_url(html, base_url)


def _check_stealth_site(url: str, *, use_proxy: bool = False) -> SourceResult:
    """慢速源通用查询 — 通过 StealthySession 浏览器渲染 + CF 绕过."""
    try:
        status, html = stealth_get(url, use_proxy=use_proxy)
        if status != 200:
            return SourceResult(
                error=f"HTTP {status}" if status else f"连接失败: {html[:40]}"
            )
        if is_cloudflare_block(html):
            return SourceResult(error="Cloudflare 拦截 (Stealthy 无法绕过)")
        version, vcode = extract_both(html)
        detail_url = _extract_detail_url_stealth(html, url)
        if version:
            return SourceResult(version=version, version_code=vcode, detail_url=detail_url)
        return SourceResult(
            version_code=vcode,
            detail_url=detail_url,
            error=f"未匹配版本 ({len(html)} 字节)",
        )
    except Exception as e:
        return SourceResult(error=f"{type(e).__name__}: {e!s}"[:80])


def check_apkvision(pkg: str) -> SourceResult:
    """APKVision — 慢速源, StealthySession 绕过 Cloudflare JS Challenge.
    TCP 在国内可达，不需要代理。
    """
    return _check_stealth_site(f"https://apkvision.org/search?q={pkg}", use_proxy=False)


def check_apkmirror(pkg: str) -> SourceResult:
    """APKMirror — 快速源, 代理 + FetcherSession 绕过 GFW.

    某些游戏先上架 APKMirror 再上 Google Play，是重要的早期发现源。
    GFW TCP 封锁需要代理, curl_cffi chrome124 模拟尝试绕过 CF。
    注: StealthySession 不支持 Clash 代理, 先用 FetcherSession。
    """
    return _check_apk_site(f"https://www.apkmirror.com/?s={pkg}")


def check_apkdl(pkg: str) -> SourceResult:
    """APKDL — 慢速源, StealthySession JS 渲染后提取版本.
    TCP 在国内可达，不需要代理。
    """
    return _check_stealth_site(f"https://apkdl.com/search?q={pkg}", use_proxy=False)


# ── 源注册表（快/慢两级）─────────────────────────────────

CheckerFunc = Callable[[str], SourceResult]

# 有效来源（2026-06）— 6 个全部激活:
#   Google Play ✓ 最权威，需代理，google-play-scraper
#   APKPure     ✓ 需代理，FetcherSession
#   APKCombo    ✓ 需代理，FetcherSession
#   APKVision   ✓ StealthySession CF 绕过
#   APKMirror   ✓ 代理 + StealthySession CF 绕过（某些游戏先上架）
#   APKDL       ✓ StealthySession JS 渲染

CHECKERS_FAST: list[tuple[str, CheckerFunc]] = [
    ("Google Play", check_google),
    ("APKPure", check_apkpure),
    ("APKCombo", check_apkcombo),
    ("APKMirror", check_apkmirror),  # FetcherSession + 代理 (StealthySession 不支持 Clash 代理)
]

CHECKERS_SLOW: list[tuple[str, CheckerFunc]] = [
    ("APKVision", check_apkvision),  # TCP 可达, 不需代理
    ("APKDL", check_apkdl),          # TCP 可达, 不需代理
]

# 合并列表（向后兼容）
CHECKERS: list[tuple[str, CheckerFunc]] = CHECKERS_FAST + CHECKERS_SLOW


# ── 并发查询入口 ─────────────────────────────────────────


def _has_version_consensus(results: dict[str, SourceResult]) -> bool:
    """检查是否至少 2 个源报告了相同版本号."""
    versions = [
        sr.version
        for sr in results.values()
        if sr and sr.version
    ]
    if len(versions) < 2:
        return False
    counts = Counter(versions)
    return counts.most_common(1)[0][1] >= 2


def query_all_sources(
    package: str,
    *,
    early_return: bool = True,
    force_all: bool = False,
) -> dict[str, SourceResult]:
    """两级并发查询所有数据源.

    1. 先并行查询快速源 (FetcherSession, 线程池)
    2. 快速源达成共识 (≥2 一致) 且非强制全查 → 跳过慢速源
    3. 否则串行查询慢速源 (StealthySession, 共享浏览器)

    Args:
        package: Android 包名.
        early_return: 快速源有共识时是否跳过慢速源.
        force_all: 强制查询所有源 (忽略 early_return).

    Returns:
        {source_name: SourceResult} 字典.
    """
    results: dict[str, SourceResult] = {}

    # Stage 1: 并发快速源
    max_fast = min(len(CHECKERS_FAST), MAX_SOURCE_WORKERS)
    with ThreadPoolExecutor(max_workers=max_fast) as executor:
        future_map: dict[Future, str] = {
            executor.submit(fn, package): name
            for name, fn in CHECKERS_FAST
        }
        for future in as_completed(future_map):
            name = future_map[future]
            try:
                results[name] = future.result()
            except Exception as e:
                logger.warning("%s 查询异常: %s", name, e)
                results[name] = SourceResult(error=f"{type(e).__name__}: {e!s}"[:100])

    # Early return: 快速源已有共识且不强制全查
    if early_return and not force_all and _has_version_consensus(results):
        logger.debug(
            "%s: 快速源已达成共识，跳过慢速源 (%s)",
            package,
            ", ".join(
                f"{n}={r.version}"
                for n, r in results.items()
                if r.version
            ),
        )
        # 空占位（保持结果结构完整）
        for name, _fn in CHECKERS_SLOW:
            results.setdefault(name, SourceResult(error="skipped (consensus reached)"))
        return results

    # Stage 2: 串行慢速源
    for name, fn in CHECKERS_SLOW:
        try:
            results[name] = fn(package)
        except Exception as e:
            logger.warning("%s 查询异常: %s", name, e)
            results[name] = SourceResult(error=f"{type(e).__name__}: {e!s}"[:100])

    return results
