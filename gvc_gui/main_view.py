"""主视图 — 统计仪表盘 + 文件选择 + 游戏表格 (v5 redesign)."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog

import customtkinter as ctk

from gvc_gui.config import (
    COL_NAME, COL_PACKAGE, COL_VER_NAME, COL_VER_CODE, COL_STATUS,
    COLUMN_HEADERS, COLUMN_WIDTHS, COLUMNS,
    ROW_UPDATE_BG, ROW_OK_BG, ROW_ERROR_BG, ROW_PENDING_BG,
    CARD_INFO_BG, CARD_WARNING_BG, CARD_SUCCESS_BG, CARD_DANGER_BG,
    BORDER_COLOR, SURFACE_BG, TEXT_PRIMARY, TEXT_SECONDARY,
    ACCENT_PRIMARY, ACCENT_HOVER, ACCENT_INFO, ACCENT_SUCCESS,
    ACCENT_WARNING, ACCENT_DANGER,
    FONT_NORMAL, FONT_SMALL, FONT_BOLD, FONT_CAPTION, FONT_STAT,
    STOP_BTN_BG, STOP_BTN_HOVER,
)

# ── 辅助：CTk 元组 → 当前模式单色 ──────────────────────


def _resolve(color) -> str:
    """将 CTk (light, dark) 颜色元组解析为当前外观模式下的单色."""
    if isinstance(color, tuple):
        idx = 0 if ctk.get_appearance_mode() == "Light" else 1
        return color[idx]
    return color


def _apply_ttk_style() -> None:
    """应用 CTk 风格化的 ttk Treeview 样式."""
    mode = ctk.get_appearance_mode()
    is_dark = mode == "Dark"

    bg = "#1E293B" if is_dark else "#FFFFFF"
    fg = "#F1F5F9" if is_dark else "#0F172A"
    heading_bg = "#0F172A" if is_dark else "#F1F5F9"
    heading_fg = "#94A3B8" if is_dark else "#64748B"
    select_bg = "#3B82F6"
    select_fg = "#FFFFFF"

    style = ttk.Style()
    style.theme_use("clam")

    style.configure("Treeview",
        background=bg, foreground=fg, fieldbackground=bg,
        borderwidth=0, font=FONT_NORMAL, rowheight=36,
    )
    style.configure("Treeview.Heading",
        background=heading_bg, foreground=heading_fg,
        font=FONT_SMALL, borderwidth=0, relief="flat", padding=(8, 6),
    )
    style.map("Treeview",
        background=[("selected", select_bg)],
        foreground=[("selected", select_fg)],
    )
    style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])

    style.configure("Vertical.TScrollbar",
        background=bg, troughcolor=bg, borderwidth=0, arrowsize=14,
    )
    style.configure("Horizontal.TScrollbar",
        background=bg, troughcolor=bg, borderwidth=0, arrowsize=14,
    )


class StatsDashboard(ctk.CTkFrame):
    """顶部统计卡片 — 总数 / 有更新 / 无变化 / 失败.

    每张卡片带左侧彩色 accent 条 + Unicode 图标 + 大数字.
    """

    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)

        # (key, title, icon, accent_color, card_bg)
        specs = [
            ("total",  "总游戏数", "≣", ACCENT_INFO,    CARD_INFO_BG),
            ("update", "有更新",   "↑", ACCENT_WARNING, CARD_WARNING_BG),
            ("ok",     "无变化",   "✓", ACCENT_SUCCESS, CARD_SUCCESS_BG),
            ("error",  "获取失败", "✗", ACCENT_DANGER,  CARD_DANGER_BG),
        ]

        self._cards: dict[str, tuple[ctk.CTkFrame, ctk.CTkLabel, ctk.CTkLabel]] = {}

        for key, title, icon, accent, card_bg in specs:
            # 外层卡片 — 边框 + 浅底色
            card = ctk.CTkFrame(
                self, fg_color=card_bg, corner_radius=10,
                border_width=1, border_color=BORDER_COLOR,
            )
            card.pack(side="left", fill="both", expand=True, padx=5, pady=4)

            # 左侧彩色 accent 条
            accent_bar = ctk.CTkFrame(card, width=5, fg_color=accent, corner_radius=0)
            accent_bar.pack(side="left", fill="y")
            accent_bar.pack_propagate(False)

            # 内容区
            content = ctk.CTkFrame(card, fg_color="transparent")
            content.pack(side="left", fill="both", expand=True, padx=(12, 12), pady=8)

            ctk.CTkLabel(
                content, text=icon,
                font=("Segoe UI Symbol", 18),
                text_color=accent, anchor="w",
            ).pack(anchor="w", pady=(2, 0))

            title_lbl = ctk.CTkLabel(
                content, text=title,
                font=FONT_CAPTION,
                text_color=TEXT_SECONDARY, anchor="w",
            )
            title_lbl.pack(anchor="w")

            value_lbl = ctk.CTkLabel(
                content, text="—",
                font=FONT_STAT,
                text_color=TEXT_PRIMARY, anchor="w",
            )
            value_lbl.pack(anchor="w", pady=(0, 2))

            self._cards[key] = (card, title_lbl, value_lbl)

    def update(self, total: int = -1, updated: int = -1, ok: int = -1, error: int = -1) -> None:
        """更新卡片数字，传 -1 表示不更新."""
        updates = {"total": total, "update": updated, "ok": ok, "error": error}
        for key, val in updates.items():
            if val >= 0:
                self._cards[key][2].configure(text=str(val))

    def reset(self) -> None:
        for key in self._cards:
            self._cards[key][2].configure(text="—")


class FilePickerFrame(ctk.CTkFrame):
    """文件选择 + 操作按钮."""

    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, corner_radius=10,
                         border_width=1, border_color=BORDER_COLOR, **kwargs)

        # 标题行
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(6, 2))

        ctk.CTkLabel(
            header, text=" Excel 数据源",
            font=FONT_BOLD,
        ).pack(side="left")

        self._info_label = ctk.CTkLabel(
            header, text="",
            font=FONT_SMALL,
            text_color=TEXT_SECONDARY,
        )
        self._info_label.pack(side="right")

        # 文件路径 + 按钮行
        action_row = ctk.CTkFrame(self, fg_color="transparent")
        action_row.pack(fill="x", padx=10, pady=(2, 8))

        self._entry_var = ctk.StringVar()
        self._entry = ctk.CTkEntry(
            action_row, textvariable=self._entry_var,
            font=FONT_NORMAL, height=36,
            placeholder_text="选择 Excel 表格文件 (.xlsx)…",
        )
        self._entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self._browse_btn = ctk.CTkButton(
            action_row, text=" 浏览 ", width=70,
            font=FONT_NORMAL,
            command=self._browse,
        )
        self._browse_btn.pack(side="left", padx=2)

        self._start_btn = ctk.CTkButton(
            action_row, text="▶  开始排查", width=110,
            font=FONT_BOLD,
            fg_color=ACCENT_PRIMARY, hover_color=ACCENT_HOVER,
            command=self._on_start,
        )
        self._start_btn.pack(side="left", padx=2)

        self._stop_btn = ctk.CTkButton(
            action_row, text=" 停止 ", width=60,
            font=FONT_NORMAL,
            fg_color=STOP_BTN_BG, hover_color=STOP_BTN_HOVER,
            command=self._on_stop,
            state="disabled",
        )
        self._stop_btn.pack(side="left", padx=2)

        # 回调
        self._on_start_cb: callable = lambda: None
        self._on_stop_cb: callable = lambda: None

    # ── API ──

    def get_path(self) -> str:
        return self._entry_var.get().strip()

    def set_path(self, path: str) -> None:
        self._entry_var.set(path)

    def set_info(self, text: str) -> None:
        self._info_label.configure(text=text)

    def set_callbacks(self, on_start: callable, on_stop: callable) -> None:
        self._on_start_cb = on_start
        self._on_stop_cb = on_stop

    def set_running(self, running: bool) -> None:
        if running:
            self._start_btn.configure(state="disabled")
            self._stop_btn.configure(state="normal")
        else:
            self._start_btn.configure(state="normal")
            self._stop_btn.configure(state="disabled")

    # ── 内部 ──

    def _browse(self) -> None:
        path = filedialog.askopenfilename(
            title="选择 Excel 表格",
            filetypes=[("Excel 文件", "*.xlsx"), ("所有文件", "*.*")],
        )
        if path:
            self._entry_var.set(path)

    def _on_start(self) -> None:
        self._on_start_cb()

    def _on_stop(self) -> None:
        self._on_stop_cb()


class GameTableFrame(ctk.CTkFrame):
    """游戏列表表格 — CTk 风格化 ttk.Treeview."""

    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, corner_radius=10, **kwargs)

        # 应用 CTk 风格化 ttk 样式
        _apply_ttk_style()

        # 表头标题
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(6, 2))
        ctk.CTkLabel(header, text=" 游戏排查结果", font=FONT_BOLD).pack(side="left")
        self._stats_hint = ctk.CTkLabel(
            header, text="", font=FONT_CAPTION, text_color=TEXT_SECONDARY,
        )
        self._stats_hint.pack(side="right")

        # Treeview + 滚动条（放在子 frame 中用 grid 管理）
        tree_frame = ctk.CTkFrame(self, fg_color="transparent")
        tree_frame.pack(fill="both", expand=True, padx=0, pady=(0, 8))
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self._tree = ttk.Treeview(
            tree_frame, columns=COLUMNS, show="headings",
            selectmode="browse",
        )
        for col in COLUMNS:
            self._tree.heading(col, text=COLUMN_HEADERS[col], anchor="w")
            self._tree.column(col, width=COLUMN_WIDTHS[col], anchor="w", minwidth=50)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew", padx=(10, 0))
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew", padx=(10, 0))

        # 行样式（解析 CTk 元组为当前模式单色）
        self._tag_update = "update"
        self._tag_ok = "ok"
        self._tag_error = "error"
        self._tag_pending = "pending"
        self._refresh_tags()

        # 右键菜单
        self._ctx_menu = tk.Menu(self._tree, tearoff=0, font=FONT_SMALL)
        self._ctx_menu.add_command(label=" 重新排查此游戏", command=self._on_recheck)
        self._ctx_menu.add_command(label=" 复制包名", command=self._on_copy_pkg)
        self._tree.bind("<Button-3>", self._show_ctx)
        self._tree.bind("<Button-2>", self._show_ctx)

        # 外观切换回调
        ctk.AppearanceModeTracker.add(self._on_appearance_changed, self)

        self._on_recheck_cb: callable | None = None
        self._on_copy_cb: callable | None = None

    def _refresh_tags(self) -> None:
        """使用当前外观模式下的颜色重新配置行标签."""
        self._tree.tag_configure(self._tag_update, background=_resolve(ROW_UPDATE_BG))
        self._tree.tag_configure(self._tag_ok, background=_resolve(ROW_OK_BG))
        self._tree.tag_configure(self._tag_error, background=_resolve(ROW_ERROR_BG))
        self._tree.tag_configure(self._tag_pending, background=_resolve(ROW_PENDING_BG))

    def _on_appearance_changed(self) -> None:
        _apply_ttk_style()
        self._refresh_tags()

    # ── API ──

    def set_callbacks(self, on_recheck: callable, on_copy: callable) -> None:
        self._on_recheck_cb = on_recheck
        self._on_copy_cb = on_copy

    def populate(self, rows_data: list[dict]) -> None:
        self._tree.delete(*self._tree.get_children())
        for i, d in enumerate(rows_data):
            self._tree.insert("", "end", iid=str(i), values=(
                f" {d.get('name', '')}",
                f" {d.get('package', '')}",
                f" {d.get('current_version', '')}",
                f" {d.get('current_version_code', '')}",
                " 等待排查…",
            ), tags=(self._tag_pending,))

    def update_row(self, index: int, result) -> None:
        try:
            iid = str(index)
            if not self._tree.exists(iid):
                return
            detail = result.update_detail or "-"
            if result.has_update:
                tag = self._tag_update
            elif result.update_detail == "获取失败":
                tag = self._tag_error
            else:
                tag = self._tag_ok

            self._tree.item(iid, values=(
                f" {result.name or result.package}",
                f" {result.package}",
                f" {result.current_backend_version}",
                f" {result.current_backend_version_code}",
                f" {detail}",
            ), tags=(tag,))

            # 更新表格头统计提示
            s = self.get_stats()
            done = s["total"] - s["pending"]
            self._stats_hint.configure(
                text=f"{done}/{s['total']} 完成"
            )
        except Exception:
            import logging
            logging.getLogger("gvc").exception("更新表格行 %d 失败", index)

    def get_selected_package(self) -> str | None:
        sel = self._tree.selection()
        if not sel:
            return None
        values = self._tree.item(sel[0], "values")
        return values[1].strip() if len(values) > 1 else None

    def clear(self) -> None:
        self._tree.delete(*self._tree.get_children())

    def get_stats(self) -> dict[str, int]:
        """从当前表格数据中统计各状态数量."""
        stats = {"total": 0, "update": 0, "ok": 0, "error": 0, "pending": 0}
        for iid in self._tree.get_children():
            tags = self._tree.item(iid, "tags")
            stats["total"] += 1
            if self._tag_update in tags:
                stats["update"] += 1
            elif self._tag_error in tags:
                stats["error"] += 1
            elif self._tag_pending in tags:
                stats["pending"] += 1
            else:
                stats["ok"] += 1
        return stats

    def _show_ctx(self, event) -> None:
        item = self._tree.identify_row(event.y)
        if item:
            self._tree.selection_set(item)
            self._ctx_menu.post(event.x_root, event.y_root)

    def _on_recheck(self) -> None:
        if self._on_recheck_cb:
            self._on_recheck_cb()

    def _on_copy_pkg(self) -> None:
        pkg = self.get_selected_package()
        if pkg:
            self.clipboard_clear()
            self.clipboard_append(pkg)
        if self._on_copy_cb:
            self._on_copy_cb()
