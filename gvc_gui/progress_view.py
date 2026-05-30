"""进度 + 日志视图 — 彩色标记 + 时间戳."""

from __future__ import annotations

from datetime import datetime

import customtkinter as ctk
from gvc_gui.config import (
    FONT_NORMAL, FONT_SMALL, FONT_MONO, FONT_BOLD,
    TEXT_PRIMARY, BORDER_COLOR,
    LOG_COLOR_UPDATE, LOG_COLOR_OK, LOG_COLOR_ERROR,
    LOG_COLOR_INFO, LOG_COLOR_TS,
)


class ProgressView(ctk.CTkFrame):
    """紧凑的进度条 + 彩色实时日志."""

    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)

        # ── 进度条行 ──
        bar_row = ctk.CTkFrame(self, fg_color="transparent")
        bar_row.pack(fill="x", padx=0, pady=(2, 2))

        self._status_label = ctk.CTkLabel(
            bar_row, text=" 就绪",
            font=FONT_BOLD,
            anchor="w",
        )
        self._status_label.pack(side="left")

        self._pct_label = ctk.CTkLabel(
            bar_row, text="",
            font=FONT_SMALL,
            width=45,
            anchor="e",
        )
        self._pct_label.pack(side="right")

        self._progress = ctk.CTkProgressBar(self, height=6, corner_radius=3)
        self._progress.pack(fill="x", padx=0, pady=(0, 4))
        self._progress.set(0)

        # ── 实时日志（彩色标记） ──
        self._log = ctk.CTkTextbox(
            self,
            font=FONT_MONO,
            fg_color=("#F1F5F9", "#0F172A"),
            text_color=TEXT_PRIMARY,
            border_width=1,
            border_color=BORDER_COLOR,
            corner_radius=8,
        )
        self._log.pack(fill="both", expand=True, padx=0, pady=(2, 0))

        # 彩色标记配置
        self._log.tag_config("update", foreground=LOG_COLOR_UPDATE)
        self._log.tag_config("ok",     foreground=LOG_COLOR_OK)
        self._log.tag_config("error",  foreground=LOG_COLOR_ERROR)
        self._log.tag_config("info",   foreground=LOG_COLOR_INFO)
        self._log.tag_config("ts",     foreground=LOG_COLOR_TS)

        self._log.configure(state="disabled")

    # ── 公共 API ──

    def reset(self, total: int) -> None:
        self._progress.set(0)
        self._pct_label.configure(text="0%")
        self._status_label.configure(text=f" 排查中… 0/{total}")
        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.configure(state="disabled")

    def update_progress(self, index: int, total: int, package: str) -> None:
        ratio = index / total
        self._progress.set(ratio)
        self._pct_label.configure(text=f"{int(ratio*100)}%")
        short = package if len(package) <= 35 else package[:32] + "..."
        self._status_label.configure(text=f" [{index}/{total}] {short}")

    def log_result(self, package: str, name: str, best_v: str, detail: str,
                   has_update: bool) -> None:
        label = (name or package)[:30]
        if has_update:
            self._log_entry("⚠", "update", "UPDATE",
                            f"{label:<32} {detail}")
        elif detail == "获取失败":
            self._log_entry("✗", "error", "FAIL",
                            f"{label:<32} {detail}")
        else:
            self._log_entry("✓", "ok", "OK",
                            f"{label:<32} {detail}")

    def log_error(self, package: str, error: str) -> None:
        self._log_entry("✗", "error", "ERR",
                        f"{package[:40]:<42} {error[:60]}")

    def log_info(self, text: str) -> None:
        self._log_entry("ℹ", "info", "INFO", text)

    def set_done(self, total: int, updated: int, failed: int) -> None:
        self._progress.set(1.0)
        self._pct_label.configure(text="100%")
        parts = [f"完成 {total} 款"]
        if updated:
            parts.append(f"{updated} 款有更新")
        if failed:
            parts.append(f"{failed} 款失败")
        self._status_label.configure(text=" " + " | ".join(parts))

    # ── 内部 ──

    def _log_entry(self, icon: str, tag: str, label: str,
                   message: str) -> None:
        """插入一条带时间戳和彩色标记的日志行."""
        ts = datetime.now().strftime("%H:%M:%S")
        self._log.configure(state="normal")
        self._log.insert("end", f"{ts}  ", "ts")
        self._log.insert("end", f"{icon} ", tag)
        self._log.insert("end", f"{label:<8}", tag)
        self._log.insert("end", f" {message}\n")
        self._log.see("end")
        self._log.configure(state="disabled")
