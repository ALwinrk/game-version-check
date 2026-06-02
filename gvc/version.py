"""版本号处理 — 标准化、比较、最佳版本判定."""

from __future__ import annotations

import re
from collections import Counter

from gvc.models import GameResult


def normalize(v: str) -> str:
    """标准化版本号字符串.

    - 去除前导 v/V
    - 空格/下划线/连字符 → 点号
    - 处理 "Varies with device"

    Examples:
        "v4.4.0" → "4.4.0"
        "4 4 0"  → "4.4.0"
        "Varies with device" → ""
    """
    if not v or v.lower() in ("varies with device", "varies"):
        return ""
    return re.sub(r'^[vV]\s*', '', re.sub(r'[\s\-_]+', '.', v.strip()))


def parse_version_tuple(v: str) -> tuple[int, ...]:
    """将版本字符串解析为整数元组以便比较.

    Examples:
        "4.4.0" → (4, 4, 0)
        "4.4"   → (4, 4)
    """
    n = normalize(v)
    if not n:
        return ()
    parts = []
    for part in n.split("."):
        try:
            parts.append(int(part))
        except ValueError:
            break
    return tuple(parts)


def compare_versions(a: str, b: str) -> int:
    """比较两个版本号.

    Returns:
        -1: a < b
         0: a == b
         1: a > b
    """
    ta, tb = parse_version_tuple(a), parse_version_tuple(b)
    if ta == tb:
        return 0
    # 补齐到相同长度
    max_len = max(len(ta), len(tb))
    ta_padded = ta + (0,) * (max_len - len(ta))
    tb_padded = tb + (0,) * (max_len - len(tb))
    if ta_padded < tb_padded:
        return -1
    return 1


def best_version(r: GameResult) -> str:
    """从多个数据源结果中判定最佳版本.

    判定策略：
    1. 版本号被 ≥2 个数据源一致报告 → 直接采纳
    2. 仅一个数据源有结果 → 采纳该源
    3. 多源均有结果但无共识 → 优先 Google Play
    4. 否则取最长版本号
    """
    versions = r.all_versions
    if not versions:
        return "无法获取"

    counts = Counter(versions)
    top = counts.most_common(1)[0]
    if top[1] >= 2 or len(versions) == 1:
        return top[0]

    if r.google.version:
        return r.google.version

    return max(versions, key=lambda v: (len(v), v))


def compare_version_codes(a: str | int, b: str | int) -> int:
    """比较两个 version code（整数比较）.

    Returns:
        -1: a < b（有更新）
         0: a == b（无变化）或无法解析
         1: a > b（a 更新）
    """
    try:
        ia, ib = int(a), int(b)
    except (ValueError, TypeError):
        return 0
    if ia < ib:
        return -1
    elif ia > ib:
        return 1
    return 0


def check_for_update(
    best_v: str,
    best_vc: str | None,
    current_v: str,
    current_vc: str,
) -> tuple[bool, str]:
    """判定是否有更新（统一的版本对比逻辑，避免重复代码）.

    Returns:
        (has_update, detail) — has_update 为 True 表示有更新,
        detail 为描述字符串（如 "vc:100→200" 或 "4.4.0→4.5.0"）.
    """
    # 策略 1：版本号对比（优先）
    if best_vc and current_vc:
        try:
            cv, bv = int(current_vc), int(best_vc)
            if cv < bv:
                return True, f"vc:{current_vc}→{best_vc}"
            # 版本号相同但版本名不同
            if cv == bv and current_v and normalize(best_v) != normalize(current_v):
                return True, f"{current_v}→{best_v} (vc:{best_vc})"
            return False, "-"
        except (ValueError, TypeError):
            pass

    # 策略 2：版本名对比
    if current_v and best_v != "无法获取" and normalize(best_v) != normalize(current_v):
        detail = f"{current_v}→{best_v}"
        if best_vc:
            detail += f" (vc:{best_vc})"
        return True, detail

    # 无变化 / 首次记录
    if not current_v and best_v != "无法获取":
        return False, "首次记录"
    return False, "-"


def best_version_code(r: GameResult) -> str:
    """从多个数据源结果中判定最佳 version code.

    判定策略（镜像 best_version）：
    1. 同一 code 被 ≥2 个源一致报告 → 直接采纳
    2. 仅一个源有 code → 采纳该源
    3. 多源均有 code 但无共识 → 取数值最大的
    4. 没有任何 code → 返回空字符串
    """
    codes = r.all_version_codes
    if not codes:
        return ""

    counts = Counter(codes)
    top = counts.most_common(1)[0]
    if top[1] >= 2 or len(codes) == 1:
        return top[0]

    # 无共识 → 取数值最大的
    try:
        return str(max(int(c) for c in codes))
    except (ValueError, TypeError):
        return codes[0]
