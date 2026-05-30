"""HTML 解析 — 从页面提取版本号和 version code."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup


# ── 版本号正则模式 ───────────────────────────────────────
_VERSION_PATTERNS: list[str] = [
    # class 含 version 的精确匹配
    r'^[\d]+\.[\d]+(?:\.[\d]+)*$',
]

_ATTR_CANDIDATES: list[str] = [
    "data-dt-version",
    "data-version",
    "data-app-version",
    "data-release-version",
    "data-versioncode",
]


def extract_version(html: str) -> str | None:
    """从 HTML 中提取版本号.

    策略（按优先级）：
    1. class 名含 "version" → 精确匹配 x.y.z
    2. data-* 属性中的版本号
    3. itemprop="version"
    4. 全文 "Version: x.y.z" 模式
    5. 全文 `>x.y.z<` 模式（兜底）
    """
    soup = BeautifulSoup(html, "html.parser")

    # 策略 1：class 名含 version
    for elem in soup.select('[class*="version"]'):
        text = elem.get_text(strip=True)
        if _is_version(text):
            return text

    # 策略 2：data-* 属性
    for attr in _ATTR_CANDIDATES:
        for elem in soup.find_all(attrs={attr: True}):
            v = elem[attr].strip()
            if re.match(r'^[\d]+\.[\d]+', v) and len(v) < 25:
                return v

    # 策略 3：Schema.org itemprop
    for elem in soup.select('[itemprop="version"]'):
        m = re.search(r'([\d]+\.[\d]+(?:\.[\d]+)?)', elem.get_text(strip=True))
        if m:
            return m.group(1)

    # 策略 4：全文 "Version: …" 模式
    text = soup.get_text()
    for pattern in [
        r'(?:Version|v\.?)\s*:?\s*([\d]+\.[\d]+(?:\.[\d]+)?)',
        r'版本[：:]\s*([\d]+\.[\d]+(?:\.[\d]+)?)',
    ]:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return m.group(1)

    # 策略 5：兜底 — 标签内嵌版本号
    m = re.search(r'>\s*([\d]+\.[\d]+\.[\d]+)\s*<', html)
    if m:
        return m.group(1)

    return None


def extract_version_code(html: str) -> str | None:
    """从 HTML 中提取 version code（3-12 位数字）.

    按特异性从高到低依次尝试 10 个模式，首个命中即返回。
    """
    # 模式 1：variant code: NNNNNN（APKCombo 常见）
    m = re.search(r'variant\s*code[:\s]*(\d{3,12})', html, re.IGNORECASE)
    if m:
        return m.group(1)

    # 模式 2：x.y.z (NNNNNN)（版本号后括号跟 code）
    for m in re.finditer(r'(\d+\.\d+\.\d+)\s*[\(（]\s*(\d{3,12})\s*[\)）]', html):
        return m.group(2)

    # 模式 3a：data-dt-versioncode="NNNNNN"（APKPure 搜索页）
    m = re.search(r'data-dt-versioncode\s*=\s*["\']?(\d{3,12})', html, re.IGNORECASE)
    if m:
        return m.group(1)

    # 模式 3b：data-versioncode="NNNNNN"
    m = re.search(r'data-versioncode\s*=\s*["\']?(\d{3,12})', html, re.IGNORECASE)
    if m:
        return m.group(1)

    # 模式 3c：data-dt-version="x.y.z" — 仅提取数字部分作为 version code
    # （APKPure 有时 version name 就是纯数字 code）

    # 模式 4：<meta> 标签内嵌 versionCode
    m = re.search(
        r'<meta\s+(?:property|name)\s*=\s*["\']?versioncode["\']?\s+content\s*=\s*["\'](\d{3,12})["\']',
        html, re.IGNORECASE,
    )
    if m:
        return m.group(1)

    # 模式 5：JSON 内嵌 "versionCode": "NNNNNN"
    m = re.search(r'["\']versionCode["\']\s*:\s*["\']?(\d{3,12})["\']?', html, re.IGNORECASE)
    if m:
        return m.group(1)

    # 模式 6：纯文本标签 "Version Code: NNNNNN"
    m = re.search(r'(?:Version\s*Code|version\s*code)\s*[：:]\s*(\d{3,12})', html, re.IGNORECASE)
    if m:
        return m.group(1)

    # 模式 7：备选 data 属性 data-app-versioncode
    m = re.search(r'data-app-versioncode\s*=\s*["\']?(\d{3,12})', html, re.IGNORECASE)
    if m:
        return m.group(1)

    # 模式 8：APK 文件名内嵌 code（_123456_.apk 或 -123456.apk）
    m = re.search(r'[_-](\d{5,12})[_.]apk', html, re.IGNORECASE)
    if m:
        return m.group(1)

    # 模式 9：定义列表 <dt>Version Code</dt><dd>NNNNNN</dd>
    m = re.search(
        r'<d[td]>\s*(?:Version\s*Code|版本代码)\s*</d[td]>\s*<d[td]>\s*(\d{3,12})\s*</d[td]>',
        html, re.IGNORECASE,
    )
    if m:
        return m.group(1)

    # 模式 10：兜底 — version/ver/vc/code 关键词后的 :或= 后接大数字
    m = re.search(
        r'(?:version|ver|vc|code)\s*[：:=]\s*(\d{4,12})\b',
        html, re.IGNORECASE,
    )
    if m:
        return m.group(1)

    return None


def _is_version(text: str) -> bool:
    """检查是否像有效版本号."""
    if not text or len(text) < 3 or len(text) > 24:
        return False
    return bool(re.match(r'^[\d]+\.[\d]+(?:\.[\d]+)*$', text))
