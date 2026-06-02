"""APK 自动下载模块 — 链接提取、架构筛选、下载管理器调度.

核心职责：
1. 从各 APK 源的详情页提取下载链接
2. 识别 APK 架构 (arm64-v8a / armeabi-v7a / universal)
3. 优先选择 64 位 APK，调起外部下载管理器下载
4. 只有 32 位时仅返回链接不下载
5. 未检测到下载管理器时走内置流式下载兜底
"""

from __future__ import annotations

import glob
import os
import re
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from gvc.config import (
    ALLOW_32BIT,
    DOWNLOAD_DIR,
    DOWNLOAD_MANAGER,
    get_proxies,
)
from gvc.logging_setup import get_logger

logger = get_logger()

# ── 架构检测 ────────────────────────────────────────────

ARCH_64BIT: set[str] = {"arm64-v8a", "arm64", "aarch64", "arm64_v8a"}
ARCH_32BIT: set[str] = {"armeabi-v7a", "armeabi", "arm", "armeabi_v7a"}
ARCH_UNIVERSAL: set[str] = {"universal", "all", "nodpi"}


def detect_arch(text: str) -> str:
    """从文件名或页面文本判断 APK 架构.

    Args:
        text: 文件名、链接文本或页面标签.

    Returns:
        'arm64-v8a' | 'armeabi-v7a' | 'universal' | 'unknown'
    """
    lower = text.lower().replace("_", "-").replace(" ", "-")

    # 精确匹配 64 位
    for arch in ARCH_64BIT:
        if arch in lower:
            return "arm64-v8a"

    # 精确匹配 32 位
    for arch in ARCH_32BIT:
        if arch in lower:
            return "armeabi-v7a"

    # 通用 / no-dpi
    for arch in ARCH_UNIVERSAL:
        if arch in lower:
            return "universal"

    # 常见变体
    if "x86_64" in lower or "x64" in lower:
        return "x86_64"
    if "x86" in lower and "x86_64" not in lower:
        return "x86"

    return "unknown"


@dataclass
class DownloadVariant:
    """单个下载变体."""
    url: str
    arch: str           # arm64-v8a / armeabi-v7a / universal / unknown
    size: str = ""      # 文件大小描述 (如 "45 MB")
    source: str = ""    # 来源名称


# ── 下载管理器 ──────────────────────────────────────────


@dataclass
class DownloadManager:
    """外部下载管理器定义."""
    name: str                          # 显示名称
    exe_paths: list[str]               # 常见安装路径 (支持通配符 *)
    url_template: str                  # 命令行模板: {exe} {url} {dir} {filename}
    note: str = ""                     # 备注


SUPPORTED_MANAGERS: list[DownloadManager] = [
    DownloadManager(
        name="Free Download Manager",
        exe_paths=[
            r"C:\Program Files\Softdeluxe\Free Download Manager\fdm.exe",
            r"C:\Program Files (x86)\Softdeluxe\Free Download Manager\fdm.exe",
        ],
        url_template='"{exe}" --addurl="{url}"',
        note="请在 FDM 中手动配置代理 (127.0.0.1:7897) 以加速下载",
    ),
    DownloadManager(
        name="Internet Download Manager",
        exe_paths=[
            r"C:\Program Files (x86)\Internet Download Manager\idman.exe",
            r"C:\Program Files\Internet Download Manager\idman.exe",
        ],
        url_template='"{exe}" /d "{url}" /p "{dir}" /f "{filename}"',
        note="请在 IDM 中手动配置代理以加速下载",
    ),
    DownloadManager(
        name="aria2",
        exe_paths=["aria2c"],  # PATH 中
        url_template=(
            '"{exe}" "{url}"'
            ' --all-proxy="{proxy}"'
            ' -d "{dir}" -o "{filename}"'
            " --console-log-level=warn"
        ),
        note="aria2 可通过 --all-proxy 直接使用代理，推荐",
    ),
    DownloadManager(
        name="Motrix",
        exe_paths=[
            r"C:\Program Files\Motrix\Motrix.exe",
            r"C:\Users\*\AppData\Local\Programs\Motrix\Motrix.exe",
        ],
        url_template='"{exe}" "{url}"',
        note="Motrix 支持传入 URL 自动添加下载任务",
    ),
]


def _find_exe(paths: list[str]) -> str | None:
    """在候选路径中查找已安装的可执行文件, 支持通配符."""
    for p in paths:
        if "*" in p:
            expanded = glob.glob(p)
            if expanded:
                return expanded[0]
        elif os.path.isfile(p):
            return p
    return None


def detect_installed_managers() -> list[DownloadManager]:
    """检测已安装的下载管理器.

    Returns:
        已安装的 DownloadManager 列表.
    """
    found: list[DownloadManager] = []
    for dm in SUPPORTED_MANAGERS:
        exe = _find_exe(dm.exe_paths)
        if exe:
            found.append(dm)
    return found


def get_download_manager(name: str | None = None) -> DownloadManager | None:
    """获取下载管理器.

    Args:
        name: 指定管理器名称 (fdm/idm/aria2/motrix) 或 None 自动选择.

    Returns:
        找到的 DownloadManager, 或 None.
    """
    installed = detect_installed_managers()

    if name and name.lower() != "auto":
        name_lower = name.lower()
        for dm in installed:
            if name_lower in dm.name.lower():
                return dm
        logger.warning("指定的下载管理器 '%s' 未找到", name)

    # 自动选择：优先 aria2 (代理支持最好)，其次第一个检测到的
    if installed:
        for dm in installed:
            if "aria2" in dm.name.lower():
                return dm
        return installed[0]
    return None


def send_to_manager(
    manager: DownloadManager,
    url: str,
    save_dir: str,
    filename: str,
) -> bool:
    """通过命令行调起下载管理器.

    用 subprocess.Popen 启动，不阻塞等待下载完成。

    Args:
        manager: 下载管理器定义.
        url: APK 直链.
        save_dir: 保存目录.
        filename: 文件名.

    Returns:
        True 如果成功调起.
    """
    exe = _find_exe(manager.exe_paths)
    if not exe:
        logger.error("%s 可执行文件未找到", manager.name)
        return False

    # 确保保存目录存在
    os.makedirs(save_dir, exist_ok=True)

    # 从配置获取代理 URL 填入模板
    proxies = get_proxies()
    proxy_url = ""
    if proxies:
        proxy_url = proxies.get("https") or proxies.get("http") or ""

    cmd = manager.url_template.format(
        exe=exe,
        url=url,
        dir=save_dir,
        filename=filename,
        proxy=proxy_url,
    )

    try:
        subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info("已调起 %s 下载: %s", manager.name, filename)
        if manager.note:
            logger.info("  ⚠ %s", manager.note)
        return True
    except Exception as e:
        logger.error("调起 %s 失败: %s", manager.name, e)
        return False


# ── 内置下载（兜底）──────────────────────────────────────


def builtin_download(url: str, save_path: str) -> bool:
    """Python 流式下载 APK (仅兜底).

    使用 httpx 或 requests 进行流式下载，大文件较慢。
    推荐优先使用外部下载管理器。

    Args:
        url: APK 直链.
        save_path: 完整保存路径.

    Returns:
        True 如果下载成功.
    """
    try:
        import requests
    except ImportError:
        logger.error("requests 未安装, 无法内置下载")
        return False

    proxies = get_proxies()
    try:
        logger.info("内置下载: %s → %s", url, save_path)
        resp = requests.get(url, stream=True, timeout=60, proxies=proxies)
        resp.raise_for_status()

        total = int(resp.headers.get("content-length", 0))
        downloaded = 0
        last_milestone = 0
        with open(save_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        milestone = downloaded // (5 * 1024 * 1024)
                        if milestone > last_milestone:
                            logger.debug(
                                "  下载进度: %.1f%% (%d/%d MB)",
                                downloaded / total * 100,
                                downloaded // (1024 * 1024),
                                total // (1024 * 1024),
                            )
                            last_milestone = milestone
        logger.info("内置下载完成: %s", save_path)
        return True
    except Exception as e:
        logger.error("内置下载失败: %s", e)
        return False


# ── 每源下载链接提取 ────────────────────────────────────


def _apkpure_extract(session, detail_url: str) -> list[DownloadVariant]:
    """APKPure 详情页下载链接提取.

    APKPure 详情页通常包含 variant 列表，带有架构标签。
    """
    from gvc.http_client import http_get
    status, html = http_get(detail_url)
    if status != 200:
        return []

    variants: list[DownloadVariant] = []
    # APKPure 下载链接通常为 /download?...
    seen_urls = set()
    for m in re.finditer(
        r'href="(/download[^"]+)"[^>]*>([^<]*)<',
        html,
    ):
        url = m.group(1)
        if not url.startswith("http"):
            url = f"https://apkpure.com{url}" if url.startswith("/") else f"https://apkpure.com/{url}"
        label = m.group(2).strip()
        if url in seen_urls:
            continue
        seen_urls.add(url)
        arch = detect_arch(label) if label else detect_arch(url)
        variants.append(DownloadVariant(url=url, arch=arch, source="APKPure"))

    # 备选: 找 data-dt-version 关联的下载按钮
    if not variants:
        for m in re.finditer(
            r'href="([^"]*?\.apk[^"]*)"',
            html,
        ):
            url = m.group(1)
            if not url.startswith("http"):
                url = f"https:{url}" if url.startswith("//") else f"https://apkpure.com{url}"
            if url in seen_urls:
                continue
            seen_urls.add(url)
            arch = detect_arch(url)
            variants.append(DownloadVariant(url=url, arch=arch, source="APKPure"))

    return variants


def _apkcombo_extract(session, detail_url: str) -> list[DownloadVariant]:
    """APKCombo 详情页下载链接提取."""
    from gvc.http_client import http_get
    status, html = http_get(detail_url)
    if status != 200:
        return []

    variants: list[DownloadVariant] = []
    seen_urls = set()

    # APKCombo: variant row 通常包含架构信息
    for m in re.finditer(
        r'href="([^"]*?\.apk[^"]*)"[^>]*>(?:[^<]*?(arm64|armeabi|universal|x86)[^<]*)<',
        html,
        re.IGNORECASE,
    ):
        url = m.group(1)
        if not url.startswith("http"):
            url = f"https:{url}" if url.startswith("//") else f"https://apkcombo.com{url}"
        if url in seen_urls:
            continue
        seen_urls.add(url)
        arch = detect_arch(m.group(2) or url)
        variants.append(DownloadVariant(url=url, arch=arch, source="APKCombo"))

    if not variants:
        for m in re.finditer(r'href="([^"]*?\.apk[^"]*)"', html):
            url = m.group(1)
            if not url.startswith("http"):
                url = f"https:{url}" if url.startswith("//") else f"https://apkcombo.com{url}"
            if url in seen_urls:
                continue
            seen_urls.add(url)
            variants.append(DownloadVariant(url=url, arch=detect_arch(url), source="APKCombo"))

    return variants


def _apkmirror_extract(session, detail_url: str) -> list[DownloadVariant]:
    """APKMirror 下载链接提取 (多步跳转).

    搜索页 → 详情页 → /download/ 中间页 → variant 列表 → 直链。
    需要使用 StealthySession 保持 cookie 跨页面。
    """
    from gvc.http_client import stealth_get

    variants: list[DownloadVariant] = []

    # Step 1: 访问详情页 (搜索结果已给)
    status, html = stealth_get(detail_url)
    if status != 200:
        return []

    # Step 2: 找到 "Download APK" 链接 (通常是 /apk/.../download/)
    download_m = re.search(
        r'href="(/apk/[^"]+?/download/[^"]*)"',
        html,
    )
    if not download_m:
        # 可能是直接的 variant 列表页
        download_m = re.search(r'href="(/apk/[^"]+?/download\b[^"]*)"', html)
    if not download_m:
        return []

    download_url = download_m.group(1)
    parsed = urlparse(detail_url)
    if not download_url.startswith("http"):
        download_url = f"{parsed.scheme}://{parsed.netloc}{download_url}"

    # Step 3: 访问 download 页 → 提取 variant 链接
    status, html = stealth_get(download_url)
    if status != 200:
        return []

    seen_urls = set()
    # Variant 行通常含架构标签和直链
    for m in re.finditer(
        r'href="([^"]*?\.apk[^"]*)"[^>]*>([^<]*?)</a>',
        html,
    ):
        url = m.group(1)
        label = m.group(2).strip()
        if url in seen_urls:
            continue
        seen_urls.add(url)

        # 构建完整 URL
        if not url.startswith("http"):
            if url.startswith("//"):
                url = f"{parsed.scheme}:{url}"
            else:
                url = f"{parsed.scheme}://{parsed.netloc}{url}"

        arch = detect_arch(f"{url} {label}")
        variants.append(DownloadVariant(url=url, arch=arch, source="APKMirror"))

    return variants


def _apkvision_extract(session, detail_url: str) -> list[DownloadVariant]:
    """APKVision 详情页下载链接提取."""
    from gvc.http_client import stealth_get
    status, html = stealth_get(detail_url)
    if status != 200:
        return []

    variants: list[DownloadVariant] = []
    seen_urls = set()
    for m in re.finditer(
        r'href="([^"]*?\.apk[^"]*)"[^>]*>([^<]*?)<',
        html,
    ):
        url = m.group(1)
        label = m.group(2).strip()
        if url in seen_urls:
            continue
        seen_urls.add(url)
        arch = detect_arch(f"{url} {label}")
        variants.append(DownloadVariant(url=url, arch=arch, source="APKVision"))
    return variants


def _apkdl_extract(session, detail_url: str) -> list[DownloadVariant]:
    """APKDL 详情页下载链接提取."""
    from gvc.http_client import stealth_get
    status, html = stealth_get(detail_url)
    if status != 200:
        return []

    variants: list[DownloadVariant] = []
    seen_urls = set()
    for m in re.finditer(
        r'href="([^"]*?\.apk[^"]*)"[^>]*>([^<]*?)<',
        html,
    ):
        url = m.group(1)
        label = m.group(2).strip()
        if url in seen_urls:
            continue
        seen_urls.add(url)
        arch = detect_arch(f"{url} {label}")
        variants.append(DownloadVariant(url=url, arch=arch, source="APKDL"))
    return variants


# 源 → 提取函数映射
_EXTRACTORS: dict[str, callable] = {
    "APKPure": _apkpure_extract,
    "APKCombo": _apkcombo_extract,
    "APKMirror": _apkmirror_extract,
    "APKVision": _apkvision_extract,
    "APKDL": _apkdl_extract,
    # Google Play 不能直接下载 APK
}


def extract_download_links(
    source_name: str,
    detail_url: str,
) -> list[DownloadVariant]:
    """从指定源的详情页提取所有下载变体.

    Args:
        source_name: 源名称 (APKPure / APKCombo / APKMirror / ...)
        detail_url: 详情页或搜索结果的 URL.

    Returns:
        DownloadVariant 列表.
    """
    extractor = _EXTRACTORS.get(source_name)
    if not extractor:
        logger.debug("%s 不支持下载链接提取", source_name)
        return []

    try:
        return extractor(None, detail_url)
    except Exception as e:
        logger.warning("%s 链接提取失败: %s", source_name, e)
        return []


# ── 主导函数 ────────────────────────────────────────────


def _pick_best_variant(variants: list[DownloadVariant]) -> DownloadVariant | None:
    """从变体列表中选最佳 (arm64-v8a > universal > armeabi-v7a)."""
    if not variants:
        return None

    # 优先级排序
    arch_rank = {
        "arm64-v8a": 0,
        "universal": 1,
        "x86_64": 2,
        "unknown": 3,
        "x86": 4,
        "armeabi-v7a": 5,
    }
    return max(variants, key=lambda v: (-arch_rank.get(v.arch, 99), v.url))


def auto_download(
    package: str,
    source_results: dict[str, object],
    best_version: str,
    download_dir: str | None = None,
    dm_name: str | None = None,
    allow_32bit: bool = False,
    dry_run: bool = False,
) -> dict:
    """自动下载最新 64 位 APK.

    流程：
    1. 筛选有版本且无错误的源
    2. 按优先级逐个尝试源获取下载链接
    3. 架构筛选：arm64-v8a / universal → 下载；armeabi-v7a → 返回链接
    4. 调起下载管理器或内置下载兜底

    Args:
        package: Android 包名.
        source_results: query_all_sources() 的返回结果.
        best_version: 最终判定的最佳版本.
        download_dir: 下载目录，默认从配置读取.
        dm_name: 下载管理器 (fdm/idm/aria2/motrix/None=auto).
        allow_32bit: 是否允许下载 32 位 APK.
        dry_run: 仅提取链接不下载.

    Returns:
        {
            "success": bool,
            "manager": str | None,
            "url": str | None,
            "file_path": str | None,
            "arch": str,
            "source": str,
            "all_variants": [DownloadVariant, ...],
            "only_32bit_urls": [str, ...],
            "error": str | None,
        }
    """
    if download_dir is None:
        download_dir = DOWNLOAD_DIR
    if dm_name is None:
        dm_name = DOWNLOAD_MANAGER or None

    # 筛选有效源
    #   - 有版本且无错误 → 直接可用
    #   - 有 detail_url 但无版本 → 也能尝试提取下载链接（版本解析失败但页面拿到了）
    valid_sources = [
        (name, sr)
        for name, sr in source_results.items()
        if sr and ((sr.version and not sr.error) or sr.detail_url)
    ]

    if not valid_sources:
        return {"success": False, "error": "无有效数据源", "all_variants": [], "only_32bit_urls": []}

    # 优先级: 有版本 > 有 detail_url > 其他; 有 version_code 的排更前
    def _source_priority(item: tuple[str, object]) -> tuple[int, int, int]:
        _name, sr = item
        has_version = 1 if (sr.version and not sr.error) else 0
        has_vc = 1 if sr.version_code else 0
        has_detail = 1 if sr.detail_url else 0
        return (has_version, has_vc, has_detail)  # 从高到低

    valid_sources.sort(key=_source_priority, reverse=True)

    # 逐个源尝试提取下载链接
    all_found: list[DownloadVariant] = []
    only_32bit: list[str] = []

    for source_name, sr in valid_sources:
        if not sr.detail_url:
            continue

        logger.info("  从 %s 提取下载链接: %s", source_name, sr.detail_url[:60])
        variants = extract_download_links(source_name, sr.detail_url)

        for v in variants:
            if v.arch == "armeabi-v7a":
                only_32bit.append(v.url)
            else:
                all_found.append(v)

        if all_found:
            break  # 找到 64 位/universal 就不再继续

    # 选出最佳变体
    best = _pick_best_variant(all_found)

    if not best and not allow_32bit:
        # 只有 32 位
        return {
            "success": False,
            "manager": None,
            "url": None,
            "file_path": None,
            "arch": "armeabi-v7a",
            "source": valid_sources[0][0] if valid_sources else "",
            "all_variants": [],
            "only_32bit_urls": only_32bit,
            "error": "仅找到 32 位 APK，不自动下载" if only_32bit else "未找到下载链接",
        }

    if not best and not only_32bit:
        return {
            "success": False,
            "manager": None,
            "url": None,
            "file_path": None,
            "arch": "",
            "source": "",
            "all_variants": [],
            "only_32bit_urls": [],
            "error": "未找到任何可下载的 APK 链接",
        }

    target_url = best.url if best else only_32bit[0]
    target_arch = best.arch if best else "armeabi-v7a"
    target_source = best.source if best else ""

    # 生成文件名
    filename = f"{package}_{best_version}_{target_arch}.apk"

    if dry_run:
        return {
            "success": True,
            "manager": None,
            "url": target_url,
            "file_path": None,
            "arch": target_arch,
            "source": target_source,
            "all_variants": all_found,
            "only_32bit_urls": only_32bit,
            "error": None,
        }

    # 尝试调起下载管理器 (32位仅输出链接，不用管理器)
    manager = get_download_manager(dm_name) if best else None

    if manager:
        sent = send_to_manager(manager, target_url, download_dir, filename)
        if sent:
            return {
                "success": True,
                "manager": manager.name,
                "url": target_url,
                "file_path": None,
                "arch": target_arch,
                "source": target_source,
                "all_variants": all_found,
                "only_32bit_urls": only_32bit,
                "error": None,
            }

    # 兜底：内置下载
    save_path = os.path.join(download_dir, filename)
    ok = builtin_download(target_url, save_path)
    return {
        "success": ok,
        "manager": None,
        "url": target_url,
        "file_path": save_path if ok else None,
        "arch": target_arch,
        "source": target_source,
        "all_variants": all_found,
        "only_32bit_urls": only_32bit,
        "error": None if ok else "内置下载失败",
    }
