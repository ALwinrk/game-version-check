"""主视图 — 统计仪表盘 + 文件选择 + 游戏表格 (v5 redesign)."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog

import customtkinter as ctk

from gvc_gui.config import (
    COL_NAME, COL_PACKAGE, COL_VER_NAME, COL_VER_CODE, COL_STATUS,
    COLUMN_HEADERS, COLUMN_WIDTHS, COLUMNS,
    ROW_UPDATE_BG, ROW_OK_BG, ROW_ERROR_BG, ROW_PENDING_BG,
    CARD_TOTAL_BG, CARD_UPDATE_BG, CARD_OK_BG, CARD_ERROR_BG, CARD_TEXT,
    FONT_NORMAL, FONT_SMALL, FONT_BOLD, FONT_HEADING,
)


class StatsDashboard(ctk.CTkFrame):
    """顶部统计卡片 — 总数 / 有更新 / 无变化 / 失败."""

    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)

        self._cards: dict[str, tuple[ctk.CTkFrame, ctk.CTkLabel, ctk.CTkLabel]] = {}

        specs = [
            ("total", "总游戏数", "0", CARD_TOTAL_BG),
            ("update", "有更新", "0", CARD_UPDATE_BG),
            ("ok", "无变化", "0", CARD_OK_BG),
            ("error", "获取失败", "0", CARD_ERROR_BG),
        ]

        for key, title, value, bg in specs:
            card = ctk.CTkFrame(self, fg_color=bg, corner_radius=10)
            card.pack(side="left", fill="both", expand=True, padx=5, pady=4)

            title_lbl = ctk.CTkLabel(
                card, text=title,
                font=FONT_SMALL,
                text_color=CARD_TEXT,
            )
            title_lbl.pack(anchor="center", pady=(8, 0))

            value_lbl = ctk.CTkLabel(
                card, text=value,
                font=FONT_HEADING,
                text_color=CARD_TEXT,
            )
            value_lbl.pack(anchor="center", pady=(0, 8))

            self._cards[key] = (card, title_lbl, value_lbl)

        # 等宽分布
        for i in range(4):
            self.grid_columnconfigure(i, weight=1)

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
        super().__init__(master, corner_radius=10, **kwargs)

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
            text_color="gray",
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
            action_row, text=" 开始排查 ", width=100,
            font=FONT_BOLD,
            command=self._on_start,
        )
        self._start_btn.pack(side="left", padx=2)

        self._stop_btn = ctk.CTkButton(
            action_row, text=" 停止 ", width=60,
            font=FONT_NORMAL,
            fg_color="#DC3545", hover_color="#B02A37",
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
    """游戏列表表格."""

    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, corner_radius=10, **kwargs)

        # 表头标题
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(6, 2))
        ctk.CTkLabel(header, text=" 游戏排查结果", font=FONT_BOLD).pack(side="left")

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

        # 行样式
        self._tag_update = "update"
        self._tag_ok = "ok"
        self._tag_error = "error"
        self._tag_pending = "pending"
        self._tree.tag_configure(self._tag_update, background=ROW_UPDATE_BG)
        self._tree.tag_configure(self._tag_ok, background=ROW_OK_BG)
        self._tree.tag_configure(self._tag_error, background=ROW_ERROR_BG)
        self._tree.tag_configure(self._tag_pending, background=ROW_PENDING_BG)

        # 右键菜单
        self._ctx_menu = tk.Menu(self._tree, tearoff=0)
        self._ctx_menu.add_command(label=" 重新排查此游戏", command=self._on_recheck)
        self._ctx_menu.add_command(label=" 复制包名", command=self._on_copy_pkg)
        self._tree.bind("<Button-3>", self._show_ctx)
        self._tree.bind("<Button-2>", self._show_ctx)

        self._on_recheck_cb: callable | None = None
        self._on_copy_cb: callable | None = None

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
        except Exception:
            pass

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
