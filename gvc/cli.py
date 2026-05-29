"""CLI 入口 — 解析命令行参数并调度."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

from gvc.logging_setup import setup_logging
from gvc.logging_setup import get_logger as _get_logger


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="游戏版本自动排查工具 v4",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
示例:
  python -m gvc 海外游戏表.xlsx
  python -m gvc --check com.tencent.ig
  python -m gvc --check com.a,com.b --current 4.0,6.5
  python -m gvc -c "com.a,com.b"
        """,
    )
    parser.add_argument("file", nargs="?", help="Excel 表格路径")
    parser.add_argument("--check", "-c", help="单独排查包名，多个用逗号分隔")
    parser.add_argument(
        "--current", "-v",
        help="当前后台版本名，多个用逗号分隔（配合 --check 使用）",
    )
    parser.add_argument("--version", action="version", version="gvc v4.0.0")
    return parser


def main(argv: list[str] | None = None) -> None:
    """主入口（可通过 argv 注入，方便测试）."""
    setup_logging()
    logger = _get_logger()

    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.check:
        _handle_check_mode(args.check, args.current)
    elif args.file:
        _handle_file_mode(args.file)
    else:
        parser.print_help()


def _handle_check_mode(check_str: str, current_str: str | None) -> None:
    """处理 --check 模式."""
    from gvc.sources import CHECKERS, query_all_sources
    from gvc.history import load_history, save_history
    from gvc.version import best_version, best_version_code, compare_version_codes, normalize

    logger = _get_logger()

    pkgs = [p.strip() for p in check_str.split(",") if p.strip()]
    if not pkgs:
        logger.error("请提供至少一个包名")
        sys.exit(1)

    cur_vers: list[str] | None = None
    if current_str:
        cur_vers = [v.strip() for v in current_str.split(",")]
        if len(cur_vers) != len(pkgs):
            logger.error(
                "--current 版本数量(%d)与包名数量(%d)不一致",
                len(cur_vers), len(pkgs),
            )
            sys.exit(1)

    logger.info("排查 %d 个包名", len(pkgs))
    history = load_history()
    new_history: dict = {}
    updated_list: list[tuple[str, str]] = []

    for i, pkg in enumerate(pkgs, 1):
        logger.info("[%d/%d] %s …", i, len(pkgs), pkg)

        source_results = query_all_sources(pkg)

        r = type("_R", (), {})()  # 快速构造 GameResult-like
        r.package = pkg
        r.google = source_results.get("Google Play")
        r.apkpure = source_results.get("APKPure")
        r.apkcombo = source_results.get("APKCombo")
        r.apkvision = source_results.get("APKVision")
        r.apkmirror = source_results.get("APKMirror")
        r.apkdl = source_results.get("APKDL")
        r.all_versions = [
            v for s in source_results.values()
            if s and (v := s.version)
        ]
        r.best_version_code = next(
            (s.version_code for s in source_results.values() if s and s.version_code),
            None,
        )

        best_v = best_version(r)
        best_vc = best_version_code(r)
        best_ts = (r.google.updated_ts if r.google else None)

        # 比对来源
        if cur_vers:
            compare_v = cur_vers[i - 1].strip()
        else:
            last = history.get(pkg, {})
            compare_v = last.get("version", "") if isinstance(last, dict) else str(last)

        # 获取用于对比的 version code
        last_vc = history.get(pkg, {}).get("version_code", "") if isinstance(history.get(pkg, {}), dict) else ""
        compare_vc = last_vc if not cur_vers else ""  # --current 模式暂不额外传 version code

        changed = False
        # 策略 1：版本号对比（优先）
        if best_vc and compare_vc:
            try:
                if int(compare_vc) < int(best_vc):
                    changed = True
            except (ValueError, TypeError):
                pass

        # 策略 2：回退版本名对比
        if not changed and compare_v and best_v != "无法获取" and normalize(best_v) != normalize(compare_v):
            changed = True

        status = "⚠ 有更新" if changed else ("✓ 无变化" if compare_v else "  首次记录")
        logger.info("  %s  %s", best_v, status)

        # 打印各数据源详情
        for name, s in source_results.items():
            if s.version:
                detail = s.version
                if s.version_code:
                    detail += f" (vc:{s.version_code})"
                if s.updated_ts and name == "Google Play":
                    detail += f" [{datetime.fromtimestamp(s.updated_ts).strftime('%Y-%m-%d')}]"
                logger.info("    %-14s %s", name, detail)
            elif s.error:
                logger.info("    %-14s ✗ %s", name, s.error[:50])

        if changed:
            detail = f"{compare_v} → {best_v}"
            logger.info("  >>> %s", detail)
            updated_list.append((pkg, detail))

        new_history[pkg] = {
            "version": best_v,
            "version_code": best_vc,
            "updated_ts": best_ts,
        }

    save_history(new_history)

    if updated_list:
        logger.info("⚠ 发现 %d 款有更新:", len(updated_list))
        for pkg, detail in updated_list:
            logger.info("   %s: %s", pkg, detail)
    else:
        logger.info("✓ 所有包名版本无变化")


def _handle_file_mode(filepath: str) -> None:
    """处理 Excel 文件模式."""
    logger = _get_logger()

    if not os.path.exists(filepath):
        logger.error("文件不存在: %s", filepath)
        sys.exit(1)

    from gvc.excel_handler import process_excel
    process_excel(filepath)
