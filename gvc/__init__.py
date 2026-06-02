"""游戏版本自动排查工具 v5.2 — package root."""

__version__ = "5.2.0"

import os
import sys


def get_chromium_executable() -> str | None:
    """定位 Chromium 浏览器可执行文件.

    优先级:
    1. PyInstaller EXE 打包后 — 在 sys._MEIPASS/chromium/ 下找
    2. 开发模式 — 在 LOCALAPPDATA/ms-playwright/ 下找

    Returns:
        chrome-headless-shell.exe 或 chrome.exe 的路径, 找不到返回 None.
    """
    if getattr(sys, "frozen", False):
        # PyInstaller: 浏览器文件在 {_MEIPASS}/chromium/
        chromium_dir = os.path.join(sys._MEIPASS, "chromium")  # type: ignore[attr-defined]
        candidates = [
            os.path.join(chromium_dir, "chrome-headless-shell.exe"),
            os.path.join(chromium_dir, "chrome.exe"),
        ]
        for exe in candidates:
            if os.path.isfile(exe):
                return exe
        return None
    else:
        # 开发模式: 标准 Playwright 安装路径
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        ms_dir = os.path.join(local_appdata, "ms-playwright")
        for root, dirs, files in os.walk(ms_dir):
            # 只搜两层 (避免遍历整个浏览器目录)
            depth = root.replace(ms_dir, "").count(os.sep)
            if depth > 2:
                continue
            for f in files:
                if f in ("chrome-headless-shell.exe", "chrome.exe"):
                    return os.path.join(root, f)
        return None
