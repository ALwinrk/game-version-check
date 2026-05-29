"""后台工作线程 — 在后台执行版本查询，通过 queue 与 GUI 主线程通信."""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass, field

from gvc.models import GameResult, SourceResult
from gvc.sources import query_all_sources
from gvc.version import best_version, best_version_code, compare_version_codes, normalize
from gvc.logging_setup import get_logger

logger = get_logger()


@dataclass
class WorkerMessage:
    """工作线程 → GUI 主线程的消息."""

    type: str  # "progress" | "result" | "error" | "done"
    package: str = ""
    index: int = 0
    total: int = 0
    game_result: GameResult | None = None
    source_results: dict[str, SourceResult] | None = None
    error_text: str = ""


class CheckWorker(threading.Thread):
    """后台排查线程 — 复用 gvc 核心查询逻辑.

    通过 threading.Thread 而非 QThread，保持与 tkinter 兼容。
    """

    def __init__(
        self,
        rows_data: list[dict],
        msg_queue: queue.Queue,
        *,
        max_game_workers: int = 3,
    ) -> None:
        super().__init__(daemon=True)
        self._rows = rows_data
        self._queue = msg_queue
        self._max_workers = max_game_workers
        self._cancel = threading.Event()

    def cancel(self) -> None:
        """协作式取消 — 在每款游戏之间检查."""
        self._cancel.set()

    def run(self) -> None:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        total = len(self._rows)

        with ThreadPoolExecutor(max_workers=min(total, self._max_workers)) as executor:
            future_map = {
                executor.submit(query_all_sources, d["package"]): d
                for d in self._rows
            }
            done = 0
            for future in as_completed(future_map):
                if self._cancel.is_set():
                    # 取消后不再处理新结果
                    for f in future_map:
                        f.cancel()
                    self._queue.put(WorkerMessage(type="done", total=total))
                    return

                d = future_map[future]
                done += 1
                pkg = d["package"]

                try:
                    source_results = future.result()
                except Exception as e:
                    logger.error("查询 %s 失败: %s", pkg, e)
                    self._queue.put(WorkerMessage(
                        type="error", package=pkg,
                        index=done, total=total,
                        error_text=f"{type(e).__name__}: {e!s}"[:100],
                    ))
                    continue

                # 构造 GameResult
                r = GameResult(
                    package=pkg,
                    name=d.get("name", ""),
                    current_backend_version=d.get("current_version", ""),
                    current_backend_version_code=d.get("current_version_code", ""),
                    google=source_results.get("Google Play", SourceResult()),
                    apkpure=source_results.get("APKPure", SourceResult()),
                    apkcombo=source_results.get("APKCombo", SourceResult()),
                    apkvision=source_results.get("APKVision", SourceResult()),
                    apkmirror=source_results.get("APKMirror", SourceResult()),
                    apkdl=source_results.get("APKDL", SourceResult()),
                )

                # 判定更新状态
                best_v = best_version(r)
                best_vc = best_version_code(r)
                cur_vn = normalize(r.current_backend_version)
                cur_vc = (r.current_backend_version_code or "").strip()

                if best_v == "无法获取":
                    r.has_update = False
                    r.update_detail = "获取失败"
                elif best_vc and cur_vc:
                    cmp = compare_version_codes(cur_vc, best_vc)
                    if cmp < 0:
                        r.has_update = True
                        r.update_detail = f"vc:{cur_vc}→{best_vc}"
                        if r.current_backend_version and normalize(best_v) != cur_vn:
                            r.update_detail += f" ({r.current_backend_version}→{best_v})"
                    elif cmp == 0:
                        if cur_vn and normalize(best_v) != cur_vn and best_v != "无法获取":
                            r.has_update = True
                            r.update_detail = f"{r.current_backend_version}→{best_v} (vc:{best_vc})"
                        else:
                            r.has_update = False
                            r.update_detail = "-"
                    else:
                        r.has_update = False
                        r.update_detail = "-"
                elif cur_vn and normalize(best_v) != cur_vn and best_v != "无法获取":
                    r.has_update = True
                    r.update_detail = f"{r.current_backend_version}→{best_v}"
                    if best_vc:
                        r.update_detail += f" (vc:{best_vc})"
                elif not cur_vn and best_v != "无法获取":
                    r.has_update = False
                    r.update_detail = "首次记录"
                else:
                    r.has_update = False
                    r.update_detail = "-"

                self._queue.put(WorkerMessage(
                    type="result", package=pkg,
                    index=done, total=total,
                    game_result=r, source_results=source_results,
                ))

        self._queue.put(WorkerMessage(type="done", total=total))
