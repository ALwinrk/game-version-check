"""CLI 入口 — 解析命令行参数并调度."""

from __future__ import annotations

import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from gvc.logging_setup import setup_logging
from gvc.logging_setup import get_logger as _get_logger


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="游戏版本自动排查工具 v5.2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
示例:
  python -m gvc 海外游戏表.xlsx
  python -m gvc --check com.tencent.ig
  python -m gvc --check com.a,com.b --current 4.0,6.5
  python -m gvc --check com.tencent.ig --download
  python -m gvc --check com.tencent.ig --download --dm aria2
  python -m gvc --check com.tencent.ig --download --dry-run
        """,
    )
    parser.add_argument("file", nargs="?", help="Excel 表格路径")
    parser.add_argument("--check", "-c", help="单独排查包名，多个用逗号分隔")
    parser.add_argument(
        "--current", "-v",
        help="当前后台版本名，多个用逗号分隔（配合 --check 使用）",
    )
    parser.add_argument(
        "--download", "-d",
        action="store_true",
        help="检测到更新后自动下载 64 位 APK",
    )
    parser.add_argument(
        "--dm",
        help="指定下载管理器: fdm / idm / aria2 / motrix / auto",
        default=None,
    )
    parser.add_argument(
        "--download-dir",
        help="下载目录 (默认 ./downloads)",
        default=None,
    )
    parser.add_argument(
        "--allow-32bit",
        action="store_true",
        help="允许下载 32 位 APK",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅输出下载链接，不实际下载",
    )
    parser.add_argument(
        "--force-all",
        action="store_true",
        help="强制查询所有 6 个源（不跳过慢速源）",
    )
    parser.add_argument("--version", action="version", version="gvc v5.2.0")
    return parser


def main(argv: list[str] | None = None) -> None:
    """主入口（可通过 argv 注入，方便测试）."""
    setup_logging()
    logger = _get_logger()

    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.check:
        _handle_check_mode(
            check_str=args.check,
            current_str=args.current,
            download=args.download,
            dm=args.dm,
            download_dir=args.download_dir,
            allow_32bit=args.allow_32bit,
            dry_run=args.dry_run,
            force_all=args.force_all,
        )
    elif args.file:
        _handle_file_mode(args.file)
    else:
        parser.print_help()


def _handle_check_mode(
    check_str: str,
    current_str: str | None,
    *,
    download: bool = False,
    dm: str | None = None,
    download_dir: str | None = None,
    allow_32bit: bool = False,
    dry_run: bool = False,
    force_all: bool = False,
) -> None:
    """处理 --check 模式 (支持多包并行)."""
    from gvc.sources import CHECKERS, query_all_sources
    from gvc.history import load_history, save_history
    from gvc.version import best_version, best_version_code, check_for_update
    from gvc.config import MAX_GAME_WORKERS

    logger = _get_logger()

    pkgs = [p.strip() for p in check_str.split(",") if p.strip()]
    if not pkgs:
        logger.error("请提供至少一个包名")
        sys.exit(1)

    cur_vers: dict[str, str] = {}
    if current_str:
        cur_list = [v.strip() for v in current_str.split(",")]
        if len(cur_list) != len(pkgs):
            logger.error(
                "--current 版本数量(%d)与包名数量(%d)不一致",
                len(cur_list), len(pkgs),
            )
            sys.exit(1)
        cur_vers = {pkg: cur_list[i] for i, pkg in enumerate(pkgs)}

    logger.info("排查 %d 个包名 (并行度: %d)", len(pkgs), MAX_GAME_WORKERS)
    if download:
        logger.info("下载模式: %s", "仅输出链接" if dry_run else f"管理器={dm or 'auto'}")

    history = load_history()
    new_history: dict = {}
    updated_list: list[tuple[str, str, str]] = []  # (pkg, detail, source_name)

    # 每个包的查询结果，用于后续下载
    all_results: dict[str, dict] = {}
    pkg_best_versions: dict[str, str] = {}

    # ── 并行查询所有包 ──
    pkg_to_index = {pkg: i for i, pkg in enumerate(pkgs)}
    done = 0

    with ThreadPoolExecutor(max_workers=min(len(pkgs), MAX_GAME_WORKERS)) as executor:
        # 下载模式：强制查全部 6 个源（需要从各源获取 detail_url 用于下载）
        _force = force_all or download
        future_map = {
            executor.submit(query_all_sources, pkg, force_all=_force): pkg
            for pkg in pkgs
        }
        for future in as_completed(future_map):
            pkg = future_map[future]
            done += 1
            i = pkg_to_index[pkg]
            logger.info("[%d/%d] %s ...", done, len(pkgs), pkg)

            try:
                source_results = future.result()
            except Exception as e:
                logger.error("查询 %s 失败: %s", pkg, e)
                continue

            all_results[pkg] = source_results

            # 用 GameResult 工厂方法（不再手拼 mock 对象）
            from gvc.models import GameResult
            r = GameResult.from_source_results(pkg, source_results)
            best_v = best_version(r)
            best_vc = best_version_code(r)
            best_ts = (r.google.updated_ts if r.google else None)
            pkg_best_versions[pkg] = best_v

            # 比对来源
            if pkg in cur_vers:
                compare_v = cur_vers[pkg]
                compare_vc = ""
            else:
                last = history.get(pkg, {})
                compare_v = last.get("version", "") if isinstance(last, dict) else str(last)
                compare_vc = last.get("version_code", "") if isinstance(last, dict) else ""

            changed, update_detail = check_for_update(best_v, best_vc, compare_v, compare_vc)

            # 找出报告最新版本的源
            updated_source = ""
            if changed:
                for name, sr in source_results.items():
                    if sr and sr.version == best_v:
                        updated_source = name
                        break

            status = "⚠ 有更新" if changed else ("✓ 无变化" if compare_v else "  首次记录")
            logger.info("  %s  %s", best_v, status)

            # 打印各数据源详情
            for name in [n for n, _ in CHECKERS]:
                s = source_results.get(name)
                if not s:
                    continue
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
                logger.info("  >>> %s", update_detail)
                updated_list.append((pkg, update_detail, updated_source))

            new_history[pkg] = {
                "version": best_v,
                "version_code": best_vc,
                "updated_ts": best_ts,
            }

    save_history(new_history)

    # ── 汇总 ──
    if updated_list:
        logger.info("⚠ 发现 %d 款有更新:", len(updated_list))
        for pkg, detail, src in updated_list:
            src_info = f" [{src}]" if src else ""
            logger.info("   %s: %s%s", pkg, detail, src_info)
    else:
        logger.info("✓ 所有包名版本无变化")

    # ── 下载 ──
    if download and updated_list:
        from gvc.downloader import auto_download

        for pkg, detail, updated_source in updated_list:
            logger.info("── 下载 %s ──", pkg)
            source_results = all_results.get(pkg, {})
            best_v = pkg_best_versions.get(pkg, "")

            result = auto_download(
                package=pkg,
                source_results=source_results,
                best_version=best_v,
                download_dir=download_dir,
                dm_name=dm,
                allow_32bit=allow_32bit,
                dry_run=dry_run,
            )

            if result["success"]:
                if dry_run:
                    logger.info("  下载链接: %s", result["url"])
                    logger.info("  架构: %s | 来源: %s", result["arch"], result["source"])
                elif result["manager"]:
                    logger.info("  已发送到 %s: %s", result["manager"], result.get("url", "")[:80])
                else:
                    logger.info("  内置下载完成: %s", result.get("file_path", ""))
            elif result.get("only_32bit_urls"):
                logger.info("  仅 32 位 APK，不自动下载:")
                for url in result["only_32bit_urls"]:
                    logger.info("    %s", url[:100])
            elif result.get("error"):
                logger.warning("  下载失败: %s", result["error"])

            # 显示所有找到的变体
            if result.get("all_variants"):
                logger.info("  找到 %d 个下载变体:", len(result["all_variants"]))
                for v in result["all_variants"][:5]:  # 最多显示 5 个
                    logger.info("    [%s] %s", v.arch, v.url[:80])


def _handle_file_mode(filepath: str) -> None:
    """处理 Excel 文件模式."""
    logger = _get_logger()

    if not os.path.exists(filepath):
        logger.error("文件不存在: %s", filepath)
        sys.exit(1)

    from gvc.excel_handler import process_excel
    process_excel(filepath)
