"""对话框 — 设置、单独排查、关于."""

from __future__ import annotations

import json
import os
import sys
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from gvc_gui.config import (
    FONT_FAMILY, FONT_HEADING, FONT_NORMAL, FONT_SMALL, FONT_BOLD,
    BORDER_COLOR, TEXT_SECONDARY, TEXT_PRIMARY,
)
from gvc_gui.main_view import _resolve


def _get_settings_path() -> str:
    """获取设置文件的可靠路径（兼容源码运行和 PyInstaller EXE）."""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "gvc_gui_settings.json")


SETTINGS_FILE = _get_settings_path()


def load_settings() -> dict:
    """加载 GUI 设置."""
    if not os.path.exists(SETTINGS_FILE):
        return {}
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings(settings: dict) -> None:
    """保存 GUI 设置."""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


class SettingsDialog(ctk.CTkToplevel):
    """设置对话框 — 使用可滚动区域确保保存按钮始终可见."""

    def __init__(self, master, settings: dict, on_save: callable) -> None:
        super().__init__(master)
        self.title("设置")
        self.geometry("480x520")
        self.resizable(False, False)
        self.grab_set()

        self._settings = dict(settings)
        self._on_save = on_save

        # 让对话框整体可以拉伸，滚动区占满剩余空间
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ═══ 可滚动内容区 ═══
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.grid(row=0, column=0, sticky="nsew", padx=4, pady=(4, 0))

        # ── 外观 ──
        self._add_section(scroll, "外观")
        ctk.CTkLabel(scroll, text="外观模式",
                     font=FONT_NORMAL).pack(anchor="w", padx=16, pady=(4, 2))
        self._mode_var = ctk.StringVar(value=self._settings.get("appearance_mode", "System"))
        ctk.CTkOptionMenu(
            scroll, values=["System", "Light", "Dark"],
            variable=self._mode_var,
            font=FONT_NORMAL,
        ).pack(fill="x", padx=16, pady=(0, 2))

        ctk.CTkLabel(scroll, text="配色主题",
                     font=FONT_NORMAL).pack(anchor="w", padx=16, pady=(6, 2))
        self._theme_var = ctk.StringVar(value=self._settings.get("color_theme", "blue"))
        ctk.CTkOptionMenu(
            scroll, values=["blue", "dark-blue", "green"],
            variable=self._theme_var,
            font=FONT_NORMAL,
        ).pack(fill="x", padx=16, pady=(0, 2))

        # ── 性能 ──
        self._add_section(scroll, "性能")
        ctk.CTkLabel(scroll, text="最大并发游戏数 (1-10)",
                     font=FONT_NORMAL).pack(anchor="w", padx=16, pady=(4, 2))
        self._workers_var = ctk.StringVar(value=str(self._settings.get("max_game_workers", 3)))
        ctk.CTkEntry(
            scroll, textvariable=self._workers_var,
            font=FONT_NORMAL,
        ).pack(fill="x", padx=16, pady=(0, 2))

        ctk.CTkLabel(scroll, text="HTTP 请求超时（秒, 5-30）",
                     font=FONT_NORMAL).pack(anchor="w", padx=16, pady=(6, 2))
        self._timeout_var = ctk.StringVar(value=str(self._settings.get("request_timeout", 10)))
        ctk.CTkEntry(
            scroll, textvariable=self._timeout_var,
            font=FONT_NORMAL,
        ).pack(fill="x", padx=16, pady=(0, 2))

        # ── 网络 ──
        self._add_section(scroll, "网络 — HTTP 代理（访问海外站点）")
        ctk.CTkLabel(scroll, text="HTTP 代理地址",
                     font=FONT_SMALL).pack(anchor="w", padx=16, pady=(4, 0))
        self._http_proxy_var = ctk.StringVar(value=self._settings.get("http_proxy", ""))
        ctk.CTkEntry(
            scroll, textvariable=self._http_proxy_var,
            font=FONT_SMALL,
            placeholder_text="例: http://127.0.0.1:7897",
        ).pack(fill="x", padx=16, pady=(0, 4))

        ctk.CTkLabel(scroll, text="HTTPS 代理地址",
                     font=FONT_SMALL).pack(anchor="w", padx=16, pady=(4, 0))
        self._https_proxy_var = ctk.StringVar(value=self._settings.get("https_proxy", ""))
        ctk.CTkEntry(
            scroll, textvariable=self._https_proxy_var,
            font=FONT_SMALL,
            placeholder_text="例: http://127.0.0.1:7897",
        ).pack(fill="x", padx=16, pady=(0, 4))

        # ── 下载 ──
        self._add_section(scroll, "下载 — APK 下载管理")
        ctk.CTkLabel(scroll, text="下载管理器",
                     font=FONT_NORMAL).pack(anchor="w", padx=16, pady=(4, 2))
        self._dm_var = ctk.StringVar(value=self._settings.get("download_manager", "auto"))
        ctk.CTkOptionMenu(
            scroll, values=["auto", "aria2", "fdm", "idm", "motrix"],
            variable=self._dm_var,
            font=FONT_NORMAL,
        ).pack(fill="x", padx=16, pady=(0, 2))

        ctk.CTkLabel(scroll, text="下载目录（留空 = ./downloads）",
                     font=FONT_SMALL).pack(anchor="w", padx=16, pady=(6, 0))
        self._download_dir_var = ctk.StringVar(value=self._settings.get("download_dir", ""))
        ctk.CTkEntry(
            scroll, textvariable=self._download_dir_var,
            font=FONT_SMALL,
            placeholder_text="例: D:\\APKs",
        ).pack(fill="x", padx=16, pady=(0, 8))

        # ── 底部留白 (让滚动区末尾不贴边) ──
        ctk.CTkLabel(scroll, text="").pack(pady=4)

        # ═══ 底部按钮栏（固定，不滚动） ═══
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(8, 12))
        btn_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            btn_frame, text="取消", command=self.destroy,
            font=FONT_NORMAL,
            fg_color=("#E2E8F0", "#334155"),
            hover_color=("#CBD5E1", "#475569"),
            text_color=TEXT_PRIMARY,
        ).pack(side="right", padx=(4, 0))

        ctk.CTkButton(
            btn_frame, text="💾 保存设置", command=self._save,
            font=FONT_BOLD, height=36,
        ).pack(side="right")

    def _add_section(self, parent, title: str) -> None:
        """添加小节分隔线 + 标题."""
        ctk.CTkFrame(parent, height=1, fg_color=BORDER_COLOR).pack(
            fill="x", padx=16, pady=(10, 2))
        ctk.CTkLabel(parent, text=title, font=FONT_SMALL,
                     text_color=TEXT_SECONDARY).pack(anchor="w", padx=16)

    def _save(self) -> None:
        try:
            w = int(self._workers_var.get())
            if not (1 <= w <= 10):
                raise ValueError
        except ValueError:
            messagebox.showwarning("设置", "最大并发游戏数必须为 1-10 的整数", parent=self)
            return
        try:
            t = int(self._timeout_var.get())
            if not (5 <= t <= 30):
                raise ValueError
        except ValueError:
            messagebox.showwarning("设置", "请求超时必须为 5-30 的整数", parent=self)
            return

        new_settings = {
            "appearance_mode": self._mode_var.get(),
            "color_theme": self._theme_var.get(),
            "max_game_workers": w,
            "request_timeout": t,
            "http_proxy": self._http_proxy_var.get().strip(),
            "https_proxy": self._https_proxy_var.get().strip(),
            "download_manager": self._dm_var.get(),
            "download_dir": self._download_dir_var.get().strip(),
        }
        self._on_save(new_settings)
        messagebox.showinfo("设置", "设置已保存 ✓", parent=self)
        self.destroy()


class SingleCheckDialog(ctk.CTkToplevel):
    """单独排查对话框."""

    def __init__(self, master) -> None:
        super().__init__(master)
        self.title("单独排查")
        self.geometry("500x420")
        self.resizable(False, False)
        self.grab_set()

        # 包名
        ctk.CTkLabel(self, text="游戏包名",
                     font=FONT_NORMAL).pack(anchor="w", padx=20, pady=(16, 2))
        self._pkg_var = ctk.StringVar()
        ctk.CTkEntry(self, textvariable=self._pkg_var,
                     font=FONT_NORMAL,
                     placeholder_text="例: com.tencent.ig").pack(fill="x", padx=20, pady=(0, 8))

        # 当前版本名（可选）
        ctk.CTkLabel(self, text="当前后台版本名（可选）",
                     font=FONT_NORMAL).pack(anchor="w", padx=20, pady=(4, 2))
        self._ver_var = ctk.StringVar()
        ctk.CTkEntry(self, textvariable=self._ver_var,
                     font=FONT_NORMAL,
                     placeholder_text="例: 4.4.0").pack(fill="x", padx=20, pady=(0, 8))

        # 当前版本号（可选）
        ctk.CTkLabel(self, text="当前后台版本号（可选）",
                     font=FONT_NORMAL).pack(anchor="w", padx=20, pady=(4, 2))
        self._vc_var = ctk.StringVar()
        ctk.CTkEntry(self, textvariable=self._vc_var,
                     font=FONT_NORMAL,
                     placeholder_text="例: 12345678").pack(fill="x", padx=20, pady=(0, 8))

        # 查询按钮
        self._check_btn = ctk.CTkButton(
            self, text="查询", command=self._do_check,
            font=FONT_NORMAL,
        )
        self._check_btn.pack(pady=(8, 4))

        # 结果展示
        self._result_text = ctk.CTkTextbox(
            self, font=FONT_SMALL,
            height=120,
        )
        self._result_text.pack(fill="both", expand=True, padx=20, pady=(8, 16))
        # 彩色标签
        self._result_text.tag_config("heading",
            foreground=_resolve(("#3B82F6", "#60A5FA")))
        self._result_text.tag_config("ok", foreground=_resolve(("#22C55E", "#4ADE80")))
        self._result_text.tag_config("err", foreground=_resolve(("#EF4444", "#F87171")))
        self._result_text.insert("1.0", "结果将显示在这里…")
        self._result_text.configure(state="disabled")

    def _do_check(self) -> None:
        pkg = self._pkg_var.get().strip()
        if not pkg:
            messagebox.showwarning("单独排查", "请输入游戏包名", parent=self)
            return

        self._check_btn.configure(text="查询中…", state="disabled")
        self._result_text.configure(state="normal")
        self._result_text.delete("1.0", "end")
        self._result_text.insert("1.0", "正在查询…\n")
        self._result_text.configure(state="disabled")
        self.update()

        import threading

        def _run() -> None:
            from gvc.models import GameResult, SourceResult
            from gvc.sources import query_all_sources
            from gvc.version import best_version, best_version_code

            results = query_all_sources(pkg)
            r = GameResult(
                package=pkg,
                google=results.get("Google Play", SourceResult()),
                apkpure=results.get("APKPure", SourceResult()),
                apkcombo=results.get("APKCombo", SourceResult()),
                apkvision=results.get("APKVision", SourceResult()),
                apkmirror=results.get("APKMirror", SourceResult()),
                apkdl=results.get("APKDL", SourceResult()),
            )
            bv = best_version(r)
            bvc = best_version_code(r)

            lines = [f"包名: {pkg}", f"最佳版本: {bv}", f"最佳版本号: {bvc or '(无)'}", ""]
            for name, s in results.items():
                if s.version:
                    line = f"  {name}: {s.version}"
                    if s.version_code:
                        line += f" (vc:{s.version_code})"
                elif s.error:
                    line = f"  {name}: ✗ {s.error[:40]}"
                else:
                    line = f"  {name}: (无数据)"
                lines.append(line)

            self.after(0, lambda: self._show_result("\n".join(lines)))

        threading.Thread(target=_run, daemon=True).start()

    def _show_result(self, text: str) -> None:
        self._result_text.configure(state="normal")
        self._result_text.delete("1.0", "end")
        for i, line in enumerate(text.split("\n")):
            if i < 3:
                self._result_text.insert("end", line + "\n", "heading")
            elif "✗" in line:
                self._result_text.insert("end", line + "\n", "err")
            elif "(无数据)" in line:
                self._result_text.insert("end", line + "\n")
            else:
                self._result_text.insert("end", line + "\n", "ok")
        self._result_text.configure(state="disabled")
        self._check_btn.configure(text="查询", state="normal")


class AboutDialog(ctk.CTkToplevel):
    """关于对话框."""

    def __init__(self, master) -> None:
        super().__init__(master)
        self.title("关于")
        self.geometry("400x300")
        self.resizable(False, False)
        self.grab_set()

        # 图标
        ctk.CTkLabel(
            self, text="🎮",
            font=("Segoe UI Symbol", 36),
        ).pack(pady=(24, 4))

        # 标题 + 版本
        ctk.CTkLabel(
            self, text="Game Version Checker",
            font=FONT_HEADING,
        ).pack()
        ctk.CTkLabel(
            self, text="v5.2.0",
            font=FONT_SMALL,
            text_color=TEXT_SECONDARY,
        ).pack(pady=(0, 12))

        # 分隔线
        ctk.CTkFrame(self, height=1, fg_color=BORDER_COLOR).pack(
            fill="x", padx=60)

        # 描述
        about_text = (
            "自动查询 Google Play + 5 个 APK 站点\n"
            "比对游戏版本变化\n"
            "支持版本名 + 版本号双重对比\n"
            "检测到更新自动下载 64 位 APK"
        )
        ctk.CTkLabel(
            self, text=about_text,
            font=FONT_SMALL,
            justify="center",
            text_color=TEXT_SECONDARY,
        ).pack(pady=(12, 8))

        ctk.CTkLabel(
            self, text="© 2025-2026 内部工作工具",
            font=("", 9),
            text_color=TEXT_SECONDARY,
        ).pack(pady=(0, 12))

        ctk.CTkButton(
            self, text="关闭", command=self.destroy,
            width=80,
        ).pack()
