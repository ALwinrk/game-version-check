# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — 游戏版本排查工具 v5 单文件打包."""

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
    # 回退：扫描常见 site-packages 路径
    import site
    for _sp in site.getsitepackages():
        _candidate = Path(_sp) / "customtkinter" / "assets" / "themes"
        if _candidate.is_dir():
            _ctk_themes_src = str(_candidate)
            break

_datas = []
if _ctk_themes_src:
    _datas.append((_ctk_themes_src, _ctk_themes_dst))

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
        # -- 其他 --
        "json",
        "queue",
        "threading",
        "concurrent.futures",
        "dataclasses",
        "collections",
        "re",
        "logging",
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
