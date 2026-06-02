"""游戏版本自动排查工具 v4 — 入口文件.

用法:
  python game_version_checker.py 海外游戏表.xlsx          # 全表排查
  python game_version_checker.py --check com.tencent.ig    # 单独排查
  python game_version_checker.py --check "pkg1,pkg2"       # 批量排查
"""

from __future__ import annotations

from gvc.cli import main

if __name__ == "__main__":
    main()
