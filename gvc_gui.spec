# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — 游戏版本排查工具 v5.2 单文件打包 (含 Scrapling + Chromium)."""

import os
import sys
from pathlib import Path

# 项目根目录
PROJ_ROOT = Path(SPECPATH)  # type: ignore[name-defined]  # noqa: F821

# ── 自动定位 CustomTkinter 主题目录 ──
_ctk_themes_src = ""
_ctk_themes_dst = "customtkinter/assets/themes"
try:
    import customtkinter as _ctk
    _ctk_root = Path(_ctk.__file__).parent
    _themes_dir = _ctk_root / "assets" / "themes"
    if _themes_dir.is_dir():
        _ctk_themes_src = str(_themes_dir)
except Exception:
    import site
    for _sp in site.getsitepackages():
        _candidate = Path(_sp) / "customtkinter" / "assets" / "themes"
        if _candidate.is_dir():
            _ctk_themes_src = str(_candidate)
            break

_datas = []
if _ctk_themes_src:
    _datas.append((_ctk_themes_src, _ctk_themes_dst))

# ── Chromium Headless Shell (StealthySession 浏览器后端) ──
_chromium_src = ""
_chromium_dst = "chromium"
_ms_playwright = os.path.join(os.environ.get("LOCALAPPDATA", ""), "ms-playwright")
_chromium_headless = os.path.join(_ms_playwright, "chromium_headless_shell-1217", "chrome-headless-shell-win64")
if os.path.isdir(_chromium_headless):
    _chromium_src = _chromium_headless
    print(f"[spec] Bundling Chromium headless shell from: {_chromium_src}")
else:
    # 尝试其他可能的路径
    _alt_paths = [
        os.path.join(_ms_playwright, "chromium-1217", "chrome-win64"),
        os.path.join(os.path.expanduser("~"), ".cache", "ms-playwright", "chromium_headless_shell-1217"),
    ]
    for _p in _alt_paths:
        if os.path.isdir(_p):
            _chromium_src = _p
            _chromium_dst = "chromium"
            print(f"[spec] Bundling Chromium from: {_chromium_src}")
            break

# ── browserforge 需要的数据文件 ──
import site
for _sp in site.getsitepackages():
    _af_data = os.path.join(_sp, "apify_fingerprint_datapoints", "data")
    if os.path.isdir(_af_data):
        _datas.append((_af_data, "apify_fingerprint_datapoints/data"))
        print(f"[spec] Bundling apify_fingerprint_datapoints data from: {_af_data}")
        break

if _chromium_src:
    _datas.append((_chromium_src, _chromium_dst))
    print(f"[spec] Chromium will be bundled as 'chromium/' in the package")
else:
    print("[spec] WARNING: Chromium not found! StealthySession will not work in the packaged EXE.")

a = Analysis(
    [str(PROJ_ROOT / "run_gui.py")],
    pathex=[str(PROJ_ROOT)],
    binaries=[],
    datas=_datas,
    hiddenimports=[
        # -- google-play-scraper 子模块 --
        "google_play_scraper",
        "google_play_scraper.features.app",
        "google_play_scraper.features.search",
        "google_play_scraper.features.suggestions",
        "google_play_scraper.features.permissions",
        "google_play_scraper.features.reviews",
        "google_play_scraper.constants.element",
        "google_play_scraper.constants.request",
        "google_play_scraper.utils",
        # -- Scrapling (new in v5.2) --
        "scrapling",
        "scrapling.fetchers",
        "scrapling.fetchers.requests",
        "scrapling.engines",
        "scrapling.engines.static",
        "scrapling.engines._browsers",
        "scrapling.engines._browsers._stealth",
        "scrapling.engines._browsers._chrome",
        "scrapling.engines._browsers._types",
        "scrapling.engines.toolbelt",
        "scrapling.engines.toolbelt.custom",
        "scrapling.engines.toolbelt.fingerprints",
        "scrapling.engines.toolbelt.proxy_rotation",
        "scrapling.core",
        "scrapling.core._types",
        "scrapling.parser",
        "scrapling.spiders",
        # -- Scrapling 依赖 (new in v5.2) --
        "browserforge",
        "browserforge.headers",
        "browserforge.fingerprints",
        "browserforge.bayesian_network",
        "apify_fingerprint_datapoints",
        "patchright",
        "patchright._impl",
        "patchright._impl._browser",
        "patchright._impl._browser_type",
        "patchright.async_api",
        "patchright.sync_api",
        "msgspec",
        # -- HTTP / 解析 --
        "curl_cffi",
        "bs4",
        "lxml",
        # -- Excel --
        "openpyxl",
        # -- GUI --
        "customtkinter",
        "customtkinter.windows",
        "customtkinter.windows.widgets",
        "tkinter",
        "tkinter.ttk",
        "tkinter.filedialog",
        "tkinter.messagebox",
        # -- 新增模块 --
        "gvc",
        "gvc.downloader",
        # -- 其他 --
        "json",
        "queue",
        "threading",
        "concurrent.futures",
        "dataclasses",
        "collections",
        "re",
        "logging",
        "subprocess",
        "glob",
        "atexit",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "pytest",
        "unittest",
        "http.server",
        "xmlrpc",
        "pydoc",
        "distutils",
        "setuptools",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="游戏版本排查工具",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,        # 不显示命令行窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,            # 可后续添加 .ico 图标
)
