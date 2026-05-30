"""GUI 常量 — 窗口、主题、字体、表格配置 (v5 redesign)."""

from __future__ import annotations

# ── 窗口 ──────────────────────────────────────────────────
WINDOW_TITLE = "Game Version Checker v5 — 游戏版本排查工具"
DEFAULT_GEOMETRY = "1200x800"
MIN_WIDTH = 1000
MIN_HEIGHT = 650

# ── 主题 ──────────────────────────────────────────────────
APPEARANCE_MODE = "System"
COLOR_THEME = "blue"

# ── 字体 ──────────────────────────────────────────────────
FONT_FAMILY = "Microsoft YaHei"
FONT_HEADING = (FONT_FAMILY, 18, "bold")
FONT_BOLD = (FONT_FAMILY, 14, "bold")
FONT_NORMAL = (FONT_FAMILY, 13)
FONT_SMALL = (FONT_FAMILY, 11)
FONT_CAPTION = (FONT_FAMILY, 10)
FONT_STAT = ("Segoe UI", 26, "bold")
FONT_MONO = ("Cascadia Code", 11)

# ── 配色 — 60-30-10 Slate/Blue 体系 ──────────────────────
# 所有颜色使用 CTk (light, dark) 元组，自动适配外观模式

# 基础层（60/30/10 法则）
BG_PRIMARY = ("#F8FAFC", "#0F172A")        # 60% — 页面背景
SURFACE_BG = ("#FFFFFF", "#1E293B")        # 30% — 卡片、面板
BORDER_COLOR = ("#E2E8F0", "#334155")      # 微妙分隔

# 文字层级
TEXT_PRIMARY = ("#0F172A", "#F1F5F9")      # 标题、正文
TEXT_SECONDARY = ("#64748B", "#94A3B8")    # 标签、说明
TEXT_DISABLED = ("#94A3B8", "#475569")     # 占位、禁用

# 强调色（10%）
ACCENT_PRIMARY = ("#3B82F6", "#60A5FA")    # 按钮、高亮
ACCENT_HOVER = ("#2563EB", "#3B82F6")      # 悬停

# 语义色彩 — 强调色条和图标
ACCENT_INFO = ("#64748B", "#94A3B8")       # slate-500 / 400
ACCENT_SUCCESS = ("#22C55E", "#4ADE80")    # green-500 / 400
ACCENT_WARNING = ("#F59E0B", "#FBBF24")    # amber-500 / 400
ACCENT_DANGER = ("#EF4444", "#F87171")     # red-500 / 400

# 卡片底色（各语义色极淡版本）
CARD_INFO_BG = ("#F1F5F9", "#1E293B")
CARD_WARNING_BG = ("#FEF3C7", "#292524")
CARD_SUCCESS_BG = ("#DCFCE7", "#052E16")
CARD_DANGER_BG = ("#FEE2E2", "#2E1515")

# 表格行底色
ROW_UPDATE_BG = ("#FFF7ED", "#2D2114")
ROW_OK_BG = ("#F0FDF4", "#0A2919")
ROW_ERROR_BG = ("#FEF2F2", "#2D1414")
ROW_PENDING_BG = ("#FAFAFA", "#1A2332")

# 日志标记色（固定单色，深/浅背景均清晰）
LOG_COLOR_UPDATE = "#F59E0B"
LOG_COLOR_OK = "#22C55E"
LOG_COLOR_ERROR = "#EF4444"
LOG_COLOR_INFO = "#64748B"
LOG_COLOR_TS = "#94A3B8"

# 状态栏
STATUS_BAR_BG = ("#F1F5F9", "#0F172A")

# 停止按钮（固定红）
STOP_BTN_BG = "#DC3545"
STOP_BTN_HOVER = "#B02A37"

# ── 兼容别名（旧代码逐步替换后可删除）────────────────────
CARD_TOTAL_BG = CARD_INFO_BG
CARD_UPDATE_BG = CARD_WARNING_BG
CARD_OK_BG = CARD_SUCCESS_BG
CARD_ERROR_BG = CARD_DANGER_BG
CARD_TEXT = TEXT_PRIMARY

# ── 表格列 ────────────────────────────────────────────────
COL_NAME = "name"
COL_PACKAGE = "package"
COL_VER_NAME = "ver_name"
COL_VER_CODE = "ver_code"
COL_STATUS = "status"

COLUMNS = (COL_NAME, COL_PACKAGE, COL_VER_NAME, COL_VER_CODE, COL_STATUS)

COLUMN_WIDTHS = {
    COL_NAME: 170,
    COL_PACKAGE: 270,
    COL_VER_NAME: 115,
    COL_VER_CODE: 105,
    COL_STATUS: 220,
}

COLUMN_HEADERS = {
    COL_NAME: "  游戏名",
    COL_PACKAGE: "  包名",
    COL_VER_NAME: "  版本名",
    COL_VER_CODE: "  版本号",
    COL_STATUS: "  排查结果",
}

# ── 轮询 ──────────────────────────────────────────────────
POLL_INTERVAL = 80
