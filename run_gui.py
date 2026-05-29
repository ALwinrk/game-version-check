"""游戏版本排查工具 v5 — GUI 启动入口.

双击此文件或在终端中运行:
    python run_gui.py

PyInstaller 打包时，此文件作为 Analysis 入口脚本。
"""

from __future__ import annotations

from gvc_gui.app import main

if __name__ == "__main__":
    main()
