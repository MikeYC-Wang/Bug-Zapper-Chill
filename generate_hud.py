#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_hud.py
================
Bug-Zapper & Chill — GitHub Profile 動態硬體 HUD 產生器。

從 GitHub GraphQL API v4 撈取一整年的 Contribution Calendar 矩陣，並且
完全使用 Python 原生字串格式化手工拼接原生 SVG 標籤（不依賴 matplotlib /
Pillow 等笨重繪圖庫），輸出一張「賽博朋克黑金硬體控制台」風格的
`profile-hud.svg`。

視覺組件：
  1. 中央核心：水平 3D 等角投影 (isometric) Commit 晶片矩陣
  2. 左側組件：過熱液態冷卻循環系統 (Liquid Cooling Loop)
  3. 右側組件：Bug 誘捕電磁防禦塔 (EM Bug Interception Tower)
  4. 機架外殼：Cyber HUD 邊框與頂 / 底部標語

環境變數：
  GH_PAT / GITHUB_TOKEN   GitHub Personal Access Token（擇一提供）
  HUD_USERNAME            要查詢的 GitHub 使用者名稱（預設 "MikeYC-Wang"）
"""

from __future__ import annotations

import math
import os
import random
import sys
from datetime import date, datetime, timezone
from typing import Dict, List, Sequence, Tuple

import requests

# ---------------------------------------------------------------------------
# 全域設定 / Canvas 常數
# ---------------------------------------------------------------------------

WIDTH, HEIGHT = 850, 380

COLOR_BG = "#050508"
COLOR_AMBER = "#ffb703"
COLOR_NEON_GREEN = "#00ffcc"
COLOR_WARNING_RED = "#ff4d4d"
COLOR_CHIP_DARK = "#161b22"
COLOR_GRID_LINE = "#2a2410"
FONT_STACK = "Consolas, 'Courier New', monospace"

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

CONTRIBUTION_QUERY = """
query ($username: String!) {
  user(login: $username) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            color
          }
        }
      }
    }
  }
}
"""

# 版面配置：(x0, y0, x1, y1) — 頂/底各留 34px 給裝飾文字列
HEADER_H = 34
FOOTER_H = 34
CONTENT_TOP = HEADER_H + 12
CONTENT_BOTTOM = HEIGHT - FOOTER_H - 8

LEFT_PANEL = (18, CONTENT_TOP, 208, CONTENT_BOTTOM)
CENTER_PANEL = (214, CONTENT_TOP, 636, CONTENT_BOTTOM)
RIGHT_PANEL = (642, CONTENT_TOP, 832, CONTENT_BOTTOM)


# ---------------------------------------------------------------------------
# 顏色工具函式
# ---------------------------------------------------------------------------

def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(rgb: Tuple[float, float, float]) -> str:
    r, g, b = (max(0, min(255, round(c))) for c in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def lerp_color(color_a: str, color_b: str, t: float) -> str:
    """在兩個十六進位色碼之間線性內插，t 需介於 0.0 ~ 1.0。"""
    t = max(0.0, min(1.0, t))
    ar, ag, ab = _hex_to_rgb(color_a)
    br, bg, bb = _hex_to_rgb(color_b)
    return _rgb_to_hex((ar + (br - ar) * t, ag + (bg - ag) * t, ab + (bb - ab) * t))


def shade(hex_color: str, factor: float) -> str:
    """將顏色乘上明暗係數（<1 變暗，>1 變亮），用於模擬立體光影面。"""
    r, g, b = _hex_to_rgb(hex_color)
    return _rgb_to_hex((r * factor, g * factor, b * factor))


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# 第一部分：GitHub GraphQL 數據源獲取
# ---------------------------------------------------------------------------

def fetch_contributions(username: str, token: str) -> Dict:
    """呼叫 GitHub GraphQL API v4，撈回一整年的 Contribution Calendar。

    回傳 dict：
      {
        "weeks": List[List[{"date": str, "count": int}]],
        "total": int,
        "today_count": int,
      }
    """
    headers = {
        "Authorization": f"bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {"query": CONTRIBUTION_QUERY, "variables": {"username": username}}

    resp = requests.post(GITHUB_GRAPHQL_URL, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if "errors" in data:
        raise RuntimeError(f"GitHub GraphQL API 回傳錯誤: {data['errors']}")

    user_node = data.get("data", {}).get("user")
    if user_node is None:
        raise RuntimeError(f"找不到使用者 '{username}'，請確認 HUD_USERNAME 是否正確。")

    calendar = user_node["contributionsCollection"]["contributionCalendar"]
    total = calendar["totalContributions"]

    weeks: List[List[Dict]] = []
    for week in calendar["weeks"]:
        days = [
            {"date": d["date"], "count": d["contributionCount"]}
            for d in week["contributionDays"]
        ]
        weeks.append(days)

    today_str = date.today().isoformat()
    today_count = 0
    for week in weeks:
        for day in week:
            if day["date"] == today_str:
                today_count = day["count"]

    return {"weeks": weeks, "total": total, "today_count": today_count}


# ---------------------------------------------------------------------------
# SVG <defs> — 發光濾鏡與漸層
# ---------------------------------------------------------------------------

def build_defs() -> str:
    return f"""
  <defs>
    <filter id="glow" x="-120%" y="-120%" width="340%" height="340%">
      <feGaussianBlur stdDeviation="2.4" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
    <filter id="glowStrong" x="-200%" y="-200%" width="500%" height="500%">
      <feGaussianBlur stdDeviation="4.5" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
    <radialGradient id="orbGlow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#fff8e6" stop-opacity="1"/>
      <stop offset="45%" stop-color="{COLOR_AMBER}" stop-opacity="0.95"/>
      <stop offset="100%" stop-color="{COLOR_AMBER}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="coolantGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#ffe8a3" stop-opacity="0.9"/>
      <stop offset="100%" stop-color="{COLOR_AMBER}" stop-opacity="0.55"/>
    </linearGradient>
    <linearGradient id="panelFade" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#0d1117" stop-opacity="0.0"/>
      <stop offset="100%" stop-color="#0d1117" stop-opacity="0.35"/>
    </linearGradient>
  </defs>"""


# ---------------------------------------------------------------------------
# 中央核心：水平 3D 等角投影晶片矩陣
# ---------------------------------------------------------------------------

def build_chip_matrix(weeks: Sequence[Sequence[Dict]], panel: Tuple[float, float, float, float]) -> str:
    """將 52~53 週 x 7 天的 Contribution 矩陣以等角投影 (isometric) 繪製成
    立體晶片方塊陣列。每個方塊由頂面 / 左側面 / 右側面三個 <polygon> 組成。
    """
    x0, y0, x1, y1 = panel
    tile = 6.6
    height_unit = 15.0
    dx = tile * math.cos(math.radians(30))
    dy = tile * math.sin(math.radians(30))
    hw, hh = dx, dy

    cells: List[Tuple[int, int, int]] = []
    for week_idx, week in enumerate(weeks):
        for day_idx, day in enumerate(week):
            cells.append((week_idx, day_idx, day["count"]))

    if not cells:
        return ""

    all_counts = [c for _, _, c in cells]
    max_count = max(all_counts) if max(all_counts) > 0 else 1

    xs = [wi - di for wi, di, _ in cells]
    ys = [wi + di for wi, di, _ in cells]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    # 置中運算：讓矩陣的水平/垂直中心對齊該面板的中心
    panel_cx = (x0 + x1) / 2
    origin_x = panel_cx - ((min_x + max_x) / 2) * dx
    # 垂直方向要預留最高晶片的凸起空間，因此底部對齊略偏上
    matrix_span_y = (max_y - min_y) * dy
    origin_y = y0 + (y1 - y0 - matrix_span_y) / 2 - min_y * dy + height_unit * 0.55

    # 畫家演算法：依 (x+y) 由小到大排序，確保後方晶片先畫、前方晶片覆蓋在上
    cells.sort(key=lambda c: (c[0] + c[1], c[0]))

    parts: List[str] = []
    for week_idx, day_idx, count in cells:
        t = 0.0 if count == 0 else clamp(0.22 + 0.78 * (count / max_count), 0.22, 1.0)
        base_color = COLOR_CHIP_DARK if count == 0 else lerp_color(COLOR_CHIP_DARK, COLOR_AMBER, t)
        z = 0.0 if count == 0 else 2.2 + t * height_unit

        bx = origin_x + (week_idx - day_idx) * dx
        by = origin_y + (week_idx + day_idx) * dy
        top_y = by - z

        n_pt = (bx, top_y - hh)
        e_pt = (bx + hw, top_y)
        s_pt = (bx, top_y + hh)
        w_pt = (bx - hw, top_y)

        top_face = [n_pt, e_pt, s_pt, w_pt]
        left_face = [w_pt, s_pt, (s_pt[0], s_pt[1] + z), (w_pt[0], w_pt[1] + z)]
        right_face = [s_pt, e_pt, (e_pt[0], e_pt[1] + z), (s_pt[0], s_pt[1] + z)]

        top_col = base_color
        left_col = shade(base_color, 0.5)
        right_col = shade(base_color, 0.75)

        def fmt(poly):
            return " ".join(f"{px:.2f},{py:.2f}" for px, py in poly)

        glow_attr = ' filter="url(#glow)"' if count > 0 and t > 0.55 else ""

        if z > 0:
            parts.append(f'<polygon points="{fmt(left_face)}" fill="{left_col}"/>')
            parts.append(f'<polygon points="{fmt(right_face)}" fill="{right_col}"/>')
        parts.append(f'<polygon points="{fmt(top_face)}" fill="{top_col}"{glow_attr}/>')

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# 左側組件：過熱液態冷卻循環系統
# ---------------------------------------------------------------------------

def compute_coolant_status(today_count: int) -> Tuple[int, str]:
    """依今日 Commit 數決定冷卻液溫度與狀態標籤。"""
    if today_count <= 0:
        return random.randint(22, 26), "STANDBY"
    if today_count <= 5:
        return random.randint(45, 58), "NOMINAL"
    if today_count <= 15:
        return random.randint(63, 76), "ACTIVE"
    return random.randint(80, 89), "OVERCLOCK"


def build_cooling_loop(panel: Tuple[float, float, float, float], today_count: int,
                        matrix_panel: Tuple[float, float, float, float]) -> str:
    x0, y0, x1, y1 = panel
    pump_rpm = random.randint(3500, 4000)
    coolant_temp, coolant_status = compute_coolant_status(today_count)

    tank_w, tank_h = 78, 128
    tank_x = x0 + (x1 - x0 - tank_w) / 2
    tank_y = y0 + 22
    liquid_fill_ratio = clamp(0.35 + (coolant_temp / 90) * 0.55, 0.35, 0.92)
    liquid_h = tank_h * liquid_fill_ratio
    liquid_y = tank_y + (tank_h - liquid_h)

    parts: List[str] = []

    # 標題
    parts.append(
        f'<text x="{x0 + (x1 - x0) / 2:.1f}" y="{y0 + 4:.1f}" text-anchor="middle" '
        f'font-family="{FONT_STACK}" font-size="10" font-weight="bold" '
        f'fill="{COLOR_AMBER}" letter-spacing="1.5">LIQUID COOLING LOOP</text>'
    )

    # 儲水箱外殼
    parts.append(
        f'<rect x="{tank_x:.1f}" y="{tank_y:.1f}" width="{tank_w}" height="{tank_h}" '
        f'rx="8" fill="#0b0d12" stroke="{COLOR_AMBER}" stroke-width="2"/>'
    )
    # 冷卻液
    parts.append(
        f'<clipPath id="tankClip"><rect x="{tank_x + 3:.1f}" y="{tank_y + 3:.1f}" '
        f'width="{tank_w - 6}" height="{tank_h - 6}" rx="6"/></clipPath>'
    )
    parts.append(
        f'<rect x="{tank_x + 3:.1f}" y="{liquid_y:.1f}" width="{tank_w - 6}" '
        f'height="{max(liquid_h - 3, 4):.1f}" fill="url(#coolantGrad)" '
        f'clip-path="url(#tankClip)" filter="url(#glow)"/>'
    )
    # 液面高光線
    parts.append(
        f'<line x1="{tank_x + 3:.1f}" y1="{liquid_y:.1f}" x2="{tank_x + tank_w - 3:.1f}" '
        f'y2="{liquid_y:.1f}" stroke="#fff3d0" stroke-width="1.2" opacity="0.8" '
        f'clip-path="url(#tankClip)"/>'
    )

    # 氣泡上升動畫
    random.seed(f"bubbles-{today_count}")
    for i in range(7):
        bx = tank_x + 10 + (i % 3) * (tank_w - 20) / 2 + random.uniform(-3, 3)
        by_start = tank_y + tank_h - 6
        by_end = liquid_y + 3
        r = round(random.uniform(1.6, 4.0), 1)
        dur = round(random.uniform(2.2, 4.2), 2)
        delay = round(random.uniform(0, 2.5), 2)
        parts.append(
            f'<circle cx="{bx:.1f}" cy="{by_start:.1f}" r="{r}" fill="#fff6dd" opacity="0.55" '
            f'clip-path="url(#tankClip)">'
            f'<animate attributeName="cy" values="{by_start:.1f};{by_end:.1f}" '
            f'dur="{dur}s" begin="{delay}s" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0.6;0" dur="{dur}s" begin="{delay}s" '
            f'repeatCount="indefinite"/>'
            f'</circle>'
        )

    # 水管：從水箱底部延伸並包覆中央矩陣的 CPU 水冷頭
    mx0, my0, mx1, my1 = matrix_panel
    cpu_x = mx0 + 6
    cpu_y = my1 - 14
    tube_start_x = tank_x + tank_w
    tube_start_y = tank_y + tank_h - 18
    tube_mid_x = (tube_start_x + cpu_x) / 2
    parts.append(
        f'<path d="M {tube_start_x:.1f},{tube_start_y:.1f} '
        f'C {tube_mid_x:.1f},{tube_start_y:.1f} {tube_mid_x:.1f},{cpu_y:.1f} {cpu_x:.1f},{cpu_y:.1f}" '
        f'fill="none" stroke="#3a2f10" stroke-width="10" stroke-linecap="round"/>'
    )
    parts.append(
        f'<path d="M {tube_start_x:.1f},{tube_start_y:.1f} '
        f'C {tube_mid_x:.1f},{tube_start_y:.1f} {tube_mid_x:.1f},{cpu_y:.1f} {cpu_x:.1f},{cpu_y:.1f}" '
        f'fill="none" stroke="{COLOR_AMBER}" stroke-width="3" stroke-linecap="round" opacity="0.85"/>'
    )
    # CPU 水冷頭方塊
    parts.append(
        f'<rect x="{cpu_x - 12:.1f}" y="{cpu_y - 12:.1f}" width="24" height="24" rx="3" '
        f'fill="#0b0d12" stroke="{COLOR_NEON_GREEN}" stroke-width="1.6" filter="url(#glow)"/>'
    )
    for fin in range(4):
        fy = cpu_y - 8 + fin * 5
        parts.append(
            f'<line x1="{cpu_x - 9:.1f}" y1="{fy:.1f}" x2="{cpu_x + 9:.1f}" y2="{fy:.1f}" '
            f'stroke="{COLOR_NEON_GREEN}" stroke-width="0.8" opacity="0.6"/>'
        )
    parts.append(
        f'<text x="{cpu_x:.1f}" y="{cpu_y - 16:.1f}" text-anchor="middle" '
        f'font-family="{FONT_STACK}" font-size="7" fill="{COLOR_NEON_GREEN}">CPU BLOCK</text>'
    )

    # 數據面板文字
    data_y = tank_y + tank_h + 22
    status_color = COLOR_WARNING_RED if coolant_status == "OVERCLOCK" else COLOR_NEON_GREEN
    parts.append(
        f'<text x="{x0 + (x1 - x0) / 2:.1f}" y="{data_y:.1f}" text-anchor="middle" '
        f'font-family="{FONT_STACK}" font-size="10.5" fill="{COLOR_AMBER}">'
        f'PUMP SPEED: {pump_rpm} RPM</text>'
    )
    parts.append(
        f'<text x="{x0 + (x1 - x0) / 2:.1f}" y="{data_y + 16:.1f}" text-anchor="middle" '
        f'font-family="{FONT_STACK}" font-size="10.5" fill="{status_color}">'
        f'COOLANT TEMP: {coolant_temp}&#176;C [{coolant_status}]</text>'
    )

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# 右側組件：Bug 誘捕電磁防禦塔
# ---------------------------------------------------------------------------

def build_bug_icon(cx: float, cy: float) -> str:
    """繪製一個掙扎中的黃色 Bug 向量圖標（橢圓身軀 + 亂舞的六隻腳 + 觸角）。"""
    return f"""<g transform="translate({cx:.1f},{cy:.1f}) rotate(-12)">
      <ellipse cx="0" cy="0" rx="13" ry="8.5" fill="#ffe066" stroke="#6b4e00" stroke-width="1.3"/>
      <line x1="-9" y1="0" x2="9" y2="0" stroke="#6b4e00" stroke-width="0.8"/>
      <line x1="-8" y1="-7" x2="-17" y2="-15" stroke="#6b4e00" stroke-width="1.6"/>
      <line x1="-2" y1="-8" x2="-5" y2="-19" stroke="#6b4e00" stroke-width="1.6"/>
      <line x1="7" y1="-7" x2="15" y2="-17" stroke="#6b4e00" stroke-width="1.6"/>
      <line x1="-8" y1="7" x2="-18" y2="12" stroke="#6b4e00" stroke-width="1.6"/>
      <line x1="1" y1="8" x2="2" y2="20" stroke="#6b4e00" stroke-width="1.6"/>
      <line x1="8" y1="7" x2="17" y2="14" stroke="#6b4e00" stroke-width="1.6"/>
      <circle cx="-6" cy="-14" r="1.3" fill="#6b4e00"/>
      <circle cx="3" cy="-15" r="1.3" fill="#6b4e00"/>
      <circle cx="-9" cy="-2.5" r="1.6" fill="#3a2900"/>
      <circle cx="-9" cy="2.5" r="1.6" fill="#3a2900"/>
    </g>"""


def build_lightning(x1: float, y1: float, x2: float, y2: float,
                     segments: int = 6, jitter: float = 10.0,
                     color: str = COLOR_NEON_GREEN, seed: str = "bolt") -> str:
    """以多節點折線模擬尖銳閃電束，並套用強發光濾鏡。"""
    rng = random.Random(seed)
    points = []
    for i in range(segments + 1):
        t = i / segments
        x = x1 + (x2 - x1) * t
        y = y1 + (y2 - y1) * t
        if 0 < i < segments:
            x += rng.uniform(-jitter, jitter)
            y += rng.uniform(-jitter * 0.5, jitter * 0.5)
        points.append((x, y))
    d = "M " + " L ".join(f"{px:.1f},{py:.1f}" for px, py in points)
    return (
        f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2.2" '
        f'stroke-linecap="round" stroke-linejoin="round" filter="url(#glowStrong)"/>'
        f'<path d="{d}" fill="none" stroke="#ffffff" stroke-width="0.8" '
        f'stroke-linecap="round" stroke-linejoin="round" opacity="0.85"/>'
    )


def compute_bugs_destroyed(today_count: int) -> int:
    """依今日 Commit 數（或自嘲式隨機數）產出消滅 Bug 統計數字。"""
    if today_count <= 0:
        return random.randint(13, 42)
    return today_count * random.randint(9, 14) + random.randint(3, 27)


def build_tesla_tower(panel: Tuple[float, float, float, float], today_count: int) -> str:
    x0, y0, x1, y1 = panel
    cx = x0 + (x1 - x0) / 2
    # 以面板底部往上量測，讓「線圈塔身 + 標靶橫排 + 數據面板」平均分配垂直空間
    base_y = y1 - 90

    bugs_destroyed = compute_bugs_destroyed(today_count)
    random.seed(f"tesla-{today_count}")

    parts: List[str] = []
    parts.append(
        f'<text x="{cx:.1f}" y="{y0 + 4:.1f}" text-anchor="middle" '
        f'font-family="{FONT_STACK}" font-size="10" font-weight="bold" '
        f'fill="{COLOR_AMBER}" letter-spacing="1">EM BUG INTERCEPTION TOWER</text>'
    )

    # 塔基座
    parts.append(
        f'<rect x="{cx - 38:.1f}" y="{base_y:.1f}" width="76" height="12" rx="3" '
        f'fill="#0b0d12" stroke="{COLOR_AMBER}" stroke-width="1.6"/>'
    )
    # 特斯拉線圈環（由寬到窄堆疊，交錯明暗色，加高間距讓塔身更修長）
    ring_count = 5
    ring_spacing = 20
    top_ring_y = base_y
    for i in range(ring_count):
        rw = 30 - i * 4.4
        ring_y = base_y - 16 - i * ring_spacing
        color = COLOR_AMBER if i % 2 == 0 else "#4a3600"
        parts.append(
            f'<ellipse cx="{cx:.1f}" cy="{ring_y:.1f}" rx="{rw:.1f}" ry="5.5" '
            f'fill="none" stroke="{color}" stroke-width="2.4"/>'
        )
        top_ring_y = ring_y
    rod_top = top_ring_y - 40
    parts.append(
        f'<line x1="{cx:.1f}" y1="{base_y - 16:.1f}" x2="{cx:.1f}" y2="{rod_top:.1f}" '
        f'stroke="#8a6d00" stroke-width="3.5"/>'
    )
    orb_cy = rod_top - 14
    # 發光電磁球
    parts.append(f'<circle cx="{cx:.1f}" cy="{orb_cy:.1f}" r="20" fill="url(#orbGlow)"/>')
    parts.append(
        f'<circle cx="{cx:.1f}" cy="{orb_cy:.1f}" r="7.5" fill="#fffaf0" filter="url(#glowStrong)"/>'
    )

    # 左右閃電束擊中點（落在塔身中段高度，讓電弧有足夠長度呈現尖銳折線感）
    target_y = orb_cy + (base_y - orb_cy) * 0.55
    bug_cx = x0 + 20
    exc_x = x1 - 6
    parts.append(build_lightning(cx - 16, orb_cy, bug_cx + 8, target_y - 4,
                                  segments=6, jitter=9, color=COLOR_NEON_GREEN,
                                  seed=f"bolt-left-{today_count}"))
    parts.append(build_lightning(cx + 16, orb_cy, exc_x - 28, target_y - 4,
                                  segments=6, jitter=9, color=COLOR_NEON_GREEN,
                                  seed=f"bolt-right-{today_count}"))

    # 左側：被擊中的 Bug + 標籤
    parts.append(build_bug_icon(bug_cx, target_y))
    parts.append(
        f'<text x="{bug_cx:.1f}" y="{target_y + 26:.1f}" text-anchor="middle" '
        f'font-family="{FONT_STACK}" font-size="7.5" font-weight="bold" '
        f'fill="{COLOR_WARNING_RED}">[TARGET DETECTED]</text>'
    )

    # 右側：被擊中的例外文字（靠右對齊，避免跨欄溢出撞上塔身）
    parts.append(
        f'<text x="{exc_x:.1f}" y="{target_y:.1f}" text-anchor="end" '
        f'font-family="{FONT_STACK}" font-size="7.6" font-weight="bold" '
        f'fill="{COLOR_WARNING_RED}" filter="url(#glow)">NullPointerException</text>'
    )
    parts.append(
        f'<text x="{exc_x:.1f}" y="{target_y + 13:.1f}" text-anchor="end" '
        f'font-family="{FONT_STACK}" font-size="7" fill="{COLOR_WARNING_RED}">at Main.run()</text>'
    )

    # 數據面板
    data_y = base_y + 34
    parts.append(
        f'<text x="{cx:.1f}" y="{data_y:.1f}" text-anchor="middle" '
        f'font-family="{FONT_STACK}" font-size="10" fill="{COLOR_NEON_GREEN}">'
        f'SHIELD INTEGRITY: ACTIVE (100%)</text>'
    )
    parts.append(
        f'<text x="{cx:.1f}" y="{data_y + 16:.1f}" text-anchor="middle" '
        f'font-family="{FONT_STACK}" font-size="10" fill="{COLOR_AMBER}">'
        f'ZAP DISCHARGE: 8.4 kV [MAX]</text>'
    )
    parts.append(
        f'<text x="{cx:.1f}" y="{data_y + 32:.1f}" text-anchor="middle" '
        f'font-family="{FONT_STACK}" font-size="10.5" font-weight="bold" fill="{COLOR_AMBER}" '
        f'filter="url(#glow)">BUGS DESTROYED: {bugs_destroyed} EXCEPTIONS</text>'
    )

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# 機架外殼與裝飾：Cyber HUD 邊框 / 頂底標語 / 分隔格線
# ---------------------------------------------------------------------------

def build_corner_bracket(x: float, y: float, size: float, flip_x: bool, flip_y: bool) -> str:
    """繪製工業風雙層 L 型科技折線邊框，可透過 flip 參數套用到四個角落。"""
    sx = -1 if flip_x else 1
    sy = -1 if flip_y else 1

    def pt(dx, dy):
        return x + dx * sx, y + dy * sy

    outer = [pt(0, size), pt(0, 0), pt(size, 0)]
    inner = [pt(6, size - 10), pt(6, 6), pt(size - 10, 6)]

    def path(points):
        return "M " + " L ".join(f"{px:.1f},{py:.1f}" for px, py in points)

    return (
        f'<path d="{path(outer)}" fill="none" stroke="{COLOR_AMBER}" stroke-width="2.4" '
        f'stroke-linecap="square"/>'
        f'<path d="{path(inner)}" fill="none" stroke="{COLOR_AMBER}" stroke-width="1.1" '
        f'opacity="0.65" stroke-linecap="square"/>'
    )


def build_borders() -> str:
    size = 30
    m = 8
    parts = [
        build_corner_bracket(m, m, size, flip_x=False, flip_y=False),
        build_corner_bracket(WIDTH - m, m, size, flip_x=True, flip_y=False),
        build_corner_bracket(m, HEIGHT - m, size, flip_x=False, flip_y=True),
        build_corner_bracket(WIDTH - m, HEIGHT - m, size, flip_x=True, flip_y=True),
    ]
    return "\n".join(parts)


def build_panel_dividers() -> str:
    """繪製面板之間的硬體格線，營造機架分區感。"""
    y0, y1 = CONTENT_TOP - 6, CONTENT_BOTTOM + 6
    parts = []
    for x in (LEFT_PANEL[2] + 3, CENTER_PANEL[2] + 3):
        parts.append(
            f'<line x1="{x}" y1="{y0}" x2="{x}" y2="{y1}" stroke="{COLOR_GRID_LINE}" '
            f'stroke-width="1.5" stroke-dasharray="2 4"/>'
        )
    parts.append(
        f'<line x1="{18}" y1="{y0}" x2="{WIDTH - 18}" y2="{y0}" stroke="{COLOR_GRID_LINE}" stroke-width="1"/>'
    )
    parts.append(
        f'<line x1="{18}" y1="{y1}" x2="{WIDTH - 18}" y2="{y1}" stroke="{COLOR_GRID_LINE}" stroke-width="1"/>'
    )
    return "\n".join(parts)


def build_header_footer(total_contributions: int) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    parts = []
    # 頂部標語
    parts.append(
        f'<text x="24" y="20" font-family="{FONT_STACK}" font-size="13" font-weight="bold" '
        f'fill="{COLOR_AMBER}" letter-spacing="1">PROJECT: Bug-Zapper &amp; Chill v1.0</text>'
    )
    parts.append(f'<circle cx="{WIDTH - 150}" cy="16" r="4" fill="{COLOR_NEON_GREEN}" filter="url(#glow)">'
                  f'<animate attributeName="opacity" values="1;0.25;1" dur="1.8s" repeatCount="indefinite"/>'
                  f'</circle>')
    parts.append(
        f'<text x="{WIDTH - 24}" y="20" text-anchor="end" font-family="{FONT_STACK}" '
        f'font-size="12" font-weight="bold" fill="{COLOR_NEON_GREEN}">SYSTEM STATUS: ONLINE</text>'
    )
    # 底部標語
    parts.append(
        f'<text x="24" y="{HEIGHT - 14}" font-family="{FONT_STACK}" font-size="11" '
        f'fill="{COLOR_AMBER}">ENGINEER: MikeYC-Wang</text>'
    )
    parts.append(
        f'<text x="{WIDTH / 2:.1f}" y="{HEIGHT - 14}" text-anchor="middle" font-family="{FONT_STACK}" '
        f'font-size="11" fill="#8a8a90">TOTAL CONTRIBUTIONS (365d): {total_contributions}</text>'
    )
    parts.append(
        f'<text x="{WIDTH - 24}" y="{HEIGHT - 14}" text-anchor="end" font-family="{FONT_STACK}" '
        f'font-size="10" fill="#5a5a60">LAST SYNC: {now}</text>'
    )
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# 組裝完整 SVG
# ---------------------------------------------------------------------------

def build_svg(contrib_data: Dict) -> str:
    weeks = contrib_data["weeks"]
    total = contrib_data["total"]
    today_count = contrib_data["today_count"]

    matrix_svg = build_chip_matrix(weeks, CENTER_PANEL)
    cooling_svg = build_cooling_loop(LEFT_PANEL, today_count, CENTER_PANEL)
    tower_svg = build_tesla_tower(RIGHT_PANEL, today_count)
    borders_svg = build_borders()
    dividers_svg = build_panel_dividers()
    header_footer_svg = build_header_footer(total)
    defs_svg = build_defs()

    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}"
     xmlns="http://www.w3.org/2000/svg" role="img"
     aria-label="Bug-Zapper &amp; Chill hardware HUD dashboard">
  <title>Bug-Zapper &amp; Chill — GitHub Contribution HUD</title>
{defs_svg}
  <rect x="0" y="0" width="{WIDTH}" height="{HEIGHT}" fill="{COLOR_BG}"/>
  <rect x="1" y="1" width="{WIDTH - 2}" height="{HEIGHT - 2}" fill="none"
        stroke="#1a1608" stroke-width="1"/>

  <g id="borders">
{borders_svg}
  </g>

  <g id="header-footer">
{header_footer_svg}
  </g>

  <g id="dividers">
{dividers_svg}
  </g>

  <g id="cooling-loop">
{cooling_svg}
  </g>

  <g id="chip-matrix">
{matrix_svg}
  </g>

  <g id="tesla-tower">
{tower_svg}
  </g>
</svg>
"""
    return svg


# ---------------------------------------------------------------------------
# 主程式進入點
# ---------------------------------------------------------------------------

def main() -> int:
    token = os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN")
    username = os.environ.get("HUD_USERNAME", "MikeYC-Wang")

    if not token:
        print("錯誤：找不到 GitHub Token，請設定環境變數 GH_PAT 或 GITHUB_TOKEN。",
              file=sys.stderr)
        return 1

    try:
        contrib_data = fetch_contributions(username, token)
        svg_content = build_svg(contrib_data)
        with open("profile-hud.svg", "w", encoding="utf-8") as f:
            f.write(svg_content)
        print(f"[OK] profile-hud.svg 已產生（使用者: {username}, "
              f"365 天總 Commit 數: {contrib_data['total']}）。")
        return 0
    except Exception as exc:  # noqa: BLE001 - 頂層防護，避免對外洩漏堆疊細節之外仍需可見錯誤
        print(f"[FAIL] 產生 HUD 失敗: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
