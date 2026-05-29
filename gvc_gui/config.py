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
FONT_BOLD = (FONT_FAMILY, 14, "bold")
FONT_HEADING = (FONT_FAMILY, 16, "bold")
FONT_NORMAL = (FONT_FAMILY, 13)
FONT_SMALL = (FONT_FAMILY, 11)
FONT_MONO = ("Cascadia Code", 11)

# ── 现代配色 ──────────────────────────────────────────────
# 统计卡片
CARD_TOTAL_BG = "#E8F0FE"
CARD_UPDATE_BG = "#FFF3CD"
CARD_OK_BG = "#D4EDDA"
CARD_ERROR_BG = "#F8D7DA"
CARD_TEXT = "#1A1A2E"

# 表格行
ROW_UPDATE_BG = "#FFF8E1"
ROW_OK_BG = "#E8F5E9"
ROW_ERROR_BG = "#FFEBEE"
ROW_PENDING_BG = "#F5F5F5"

# 品牌色
BRAND_PRIMARY = "#1A73E8"
BRAND_DARK = "#0D47A1"
SIDEBAR_BG = "#F8F9FA"

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
