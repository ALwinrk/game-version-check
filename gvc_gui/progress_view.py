"""进度 + 日志视图 — 现代化设计."""

from __future__ import annotations

import customtkinter as ctk
from gvc_gui.config import FONT_NORMAL, FONT_SMALL, FONT_MONO, FONT_BOLD


class ProgressView(ctk.CTkFrame):
    """紧凑的进度条 + 实时日志."""

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

        # ── 实时日志 ──
        self._log = ctk.CTkTextbox(
            self,
            font=FONT_MONO,
            fg_color="#1E1E2E" if ctk.get_appearance_mode() == "Dark" else "#FAFAFA",
            text_color="#CDD6F4" if ctk.get_appearance_mode() == "Dark" else "#333333",
            border_width=1,
            border_color=("#E0E0E0", "#333333"),
        )
        self._log.pack(fill="both", expand=True, padx=0, pady=(2, 0))
        self._log.configure(state="disabled")

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

    def log_result(self, package: str, name: str, best_v: str, detail: str, has_update: bool) -> None:
        self._log.configure(state="normal")
        if has_update:
            icon = "!"
            tag = "UPDATE"
        elif detail == "获取失败":
            icon = "x"
            tag = "FAIL "
        else:
            icon = "+"
            tag = "OK   "
        label = (name or package)[:28]
        self._log.insert("end", f" [{icon}] {tag}  {label:<30}  {detail}\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    def log_error(self, package: str, error: str) -> None:
        self._log.configure(state="normal")
        self._log.insert("end", f" [x] ERR   {package[:40]:<42}  {error[:60]}\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    def log_info(self, text: str) -> None:
        self._log.configure(state="normal")
        self._log.insert("end", f"      INFO  {text}\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    def set_done(self, total: int, updated: int, failed: int) -> None:
        self._progress.set(1.0)
        self._pct_label.configure(text="100%")
        parts = [f"完成 {total} 款"]
        if updated:
            parts.append(f"{updated} 款有更新")
        if failed:
            parts.append(f"{failed} 款失败")
        self._status_label.configure(text=" " + " | ".join(parts))
