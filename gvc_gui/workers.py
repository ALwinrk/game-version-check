"""后台工作线程 — 在后台执行版本查询，通过 queue 与 GUI 主线程通信."""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

from gvc.models import GameResult, SourceResult
from gvc.sources import query_all_sources
from gvc.version import best_version, best_version_code, check_for_update, normalize
from gvc.logging_setup import get_logger

logger = get_logger()


@dataclass
class WorkerMessage:
    """工作线程 → GUI 主线程的消息."""

    type: str  # "progress" | "result" | "error" | "done"
    package: str = ""
    index: int = 0       # 原始 rows_data 中的位置（0-based）
    total: int = 0
    game_result: GameResult | None = None
    source_results: dict[str, SourceResult] | None = None
    error_text: str = ""


class CheckWorker(threading.Thread):
    """后台排查线程 — 复用 gvc 核心查询逻辑."""

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
        total = len(self._rows)
        if total == 0:
            self._queue.put(WorkerMessage(type="done", total=0))
            return

        with ThreadPoolExecutor(max_workers=min(total, self._max_workers)) as executor:
            # 记录每行数据的原始索引
            future_map = {
                executor.submit(query_all_sources, d["package"]): (i, d)
                for i, d in enumerate(self._rows)
            }
            done = 0
            for future in as_completed(future_map):
                if self._cancel.is_set():
                    for f in future_map:
                        f.cancel()
                    self._queue.put(WorkerMessage(type="done", total=total))
                    return

                row_index, d = future_map[future]
                done += 1
                pkg = d["package"]

                try:
                    source_results = future.result(timeout=120)
                except Exception as e:
                    logger.exception("查询 %s 失败", pkg)
                    self._queue.put(WorkerMessage(
                        type="error", package=pkg,
                        index=row_index, total=total,
                        error_text=f"{type(e).__name__}: {e!s}"[:100],
                    ))
                    continue

                r = GameResult.from_source_results(
                    pkg,
                    source_results,
                    name=d.get("name", ""),
                    current_version=d.get("current_version", ""),
                    current_version_code=d.get("current_version_code", ""),
                )

                best_v = best_version(r)
                best_vc = best_version_code(r)
                cur_vn = d.get("current_version", "")
                cur_vc = (d.get("current_version_code", "") or "").strip()

                if best_v == "无法获取":
                    r.has_update = False
                    r.update_detail = "获取失败"
                else:
                    has_update, detail = check_for_update(
                        best_v, best_vc, cur_vn, cur_vc,
                    )
                    r.has_update = has_update
                    r.update_detail = detail

                self._queue.put(WorkerMessage(
                    type="result", package=pkg,
                    index=row_index, total=total,
                    game_result=r, source_results=source_results,
                ))

        self._queue.put(WorkerMessage(type="done", total=total))
