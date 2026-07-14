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
  1. 左側組件：過熱液態冷卻循環系統 (Liquid Cooling System)
  2. 右側組件：Bug 誘捕電磁防禦塔 (EM Bug Interceptor)
  3. 機架外殼：Cyber HUD 邊框與頂 / 底部標語

環境變數：
  GH_PAT / GITHUB_TOKEN   GitHub Personal Access Token（擇一提供）
  HUD_USERNAME            要查詢的 GitHub 使用者名稱（預設 "MikeYC-Wang"）
"""

from __future__ import annotations

import os
import random
import sys
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Tuple

import requests

# ---------------------------------------------------------------------------
# 全域設定 / Canvas 常數
# ---------------------------------------------------------------------------

WIDTH, HEIGHT = 850, 380

COLOR_BG = "#050508"
COLOR_AMBER = "#ffb703"
COLOR_NEON_GREEN = "#00ffcc"
COLOR_WARNING_RED = "#ff4d4d"
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

PANEL_GAP = 14
PANEL_MID = WIDTH / 2
LEFT_PANEL = (18, CONTENT_TOP, PANEL_MID - PANEL_GAP / 2, CONTENT_BOTTOM)
RIGHT_PANEL = (PANEL_MID + PANEL_GAP / 2, CONTENT_TOP, WIDTH - 18, CONTENT_BOTTOM)


# ---------------------------------------------------------------------------
# 顏色工具函式
# ---------------------------------------------------------------------------

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
      <stop offset="0%" stop-color="#eafffa" stop-opacity="1"/>
      <stop offset="45%" stop-color="{COLOR_NEON_GREEN}" stop-opacity="0.95"/>
      <stop offset="100%" stop-color="{COLOR_NEON_GREEN}" stop-opacity="0"/>
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
# 共用小工具：面板標題列（icon + 標題文字 + 狀態指示燈）
# ---------------------------------------------------------------------------

def build_panel_title(panel: Tuple[float, float, float, float], icon: str,
                       title: str, dot_color: str) -> str:
    x0, y0, x1, _ = panel
    parts = [
        f'<text x="{x0 + 2:.1f}" y="{y0 + 6:.1f}" font-family="{FONT_STACK}" '
        f'font-size="15">{icon}</text>',
        f'<text x="{x0 + 24:.1f}" y="{y0 + 4:.1f}" font-family="{FONT_STACK}" '
        f'font-size="12.5" font-weight="bold" fill="{COLOR_AMBER}" '
        f'letter-spacing="1.2">{title}</text>',
        f'<circle cx="{x1 - 10:.1f}" cy="{y0 - 1:.1f}" r="4.5" fill="{dot_color}" '
        f'filter="url(#glow)">'
        f'<animate attributeName="opacity" values="1;0.35;1" dur="2.2s" '
        f'repeatCount="indefinite"/></circle>',
    ]
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


def compute_sys_pressure(coolant_temp: int) -> Tuple[float, str]:
    """依冷卻液溫度模擬循環系統壓力（溫度越高，壓力越大）。"""
    pressure = round(1.05 + (coolant_temp / 90) * 0.45, 2)
    status = "HIGH" if pressure > 1.3 else "NOMINAL"
    return pressure, status


def build_cooling_loop(panel: Tuple[float, float, float, float], today_count: int) -> str:
    """繪製左側過熱液態冷卻循環系統：儲液罐 + 矩形迴路水管 + CPU 水冷頭。"""
    x0, y0, x1, y1 = panel
    cx = x0 + (x1 - x0) / 2
    # 以「今天日期 + 今日 Commit 數」作為種子：同一天內只要 Commit 數沒變，
    # 重複執行就會產生完全相同的數值，避免高頻排程造成無意義的雜訊 commit。
    random.seed(f"cooling-{date.today().isoformat()}-{today_count}")
    pump_rpm = random.randint(3500, 4000)
    coolant_temp, coolant_status = compute_coolant_status(today_count)
    sys_pressure, pressure_status = compute_sys_pressure(coolant_temp)

    parts: List[str] = [build_panel_title(panel, "\U0001f9ea", "LIQUID COOLING SYSTEM", COLOR_AMBER)]

    diagram_top = y0 + 26
    diagram_h = 150

    # 矩形迴路水管：儲液罐位於左側垂直邊、CPU 水冷頭位於右側垂直邊
    loop_x0 = x0 + (x1 - x0) * 0.18
    loop_x1 = x0 + (x1 - x0) * 0.62
    loop_y0 = diagram_top + 6
    loop_y1 = diagram_top + diagram_h - 6
    loop_w = loop_x1 - loop_x0
    loop_h = loop_y1 - loop_y0
    parts.append(
        f'<rect x="{loop_x0:.1f}" y="{loop_y0:.1f}" width="{loop_w:.1f}" height="{loop_h:.1f}" '
        f'rx="18" fill="none" stroke="#3a2f10" stroke-width="12"/>'
    )
    parts.append(
        f'<rect x="{loop_x0:.1f}" y="{loop_y0:.1f}" width="{loop_w:.1f}" height="{loop_h:.1f}" '
        f'rx="18" fill="none" stroke="{COLOR_AMBER}" stroke-width="4" opacity="0.9"/>'
    )
    # 流動的冷卻液高光：以移動的虛線段模擬管內液體持續循環流動，
    # 流速依 PUMP SPEED 連動（轉速越高，流動越快）。
    flow_dur = round(clamp(1.4 - (pump_rpm - 3500) / 500 * 0.5, 0.9, 1.4), 2)
    parts.append(
        f'<rect x="{loop_x0:.1f}" y="{loop_y0:.1f}" width="{loop_w:.1f}" height="{loop_h:.1f}" '
        f'rx="18" fill="none" stroke="#fff6dd" stroke-width="2.6" stroke-linecap="round" '
        f'stroke-dasharray="9 15" opacity="0.85">'
        f'<animate attributeName="stroke-dashoffset" from="0" to="-24" '
        f'dur="{flow_dur}s" repeatCount="indefinite"/>'
        f'</rect>'
    )

    # 儲液罐（覆蓋在迴路左側垂直邊上）
    tank_w, tank_h = 62, loop_h * 0.72
    tank_x = loop_x0 - tank_w / 2
    tank_y = loop_y0 + (loop_h - tank_h) / 2
    liquid_fill_ratio = clamp(0.35 + (coolant_temp / 90) * 0.55, 0.35, 0.92)
    liquid_h = tank_h * liquid_fill_ratio
    liquid_y = tank_y + (tank_h - liquid_h)

    parts.append(
        f'<rect x="{tank_x:.1f}" y="{tank_y:.1f}" width="{tank_w}" height="{tank_h:.1f}" '
        f'rx="8" fill="#0b0d12" stroke="{COLOR_AMBER}" stroke-width="2"/>'
    )
    # 上蓋（深色端蓋，呼應參考圖的雙色罐頭造型）
    parts.append(
        f'<rect x="{tank_x:.1f}" y="{tank_y:.1f}" width="{tank_w}" height="{tank_h * 0.22:.1f}" '
        f'rx="8" fill="#1c2029" stroke="{COLOR_AMBER}" stroke-width="1.4"/>'
    )
    parts.append(
        f'<clipPath id="tankClip"><rect x="{tank_x + 3:.1f}" y="{tank_y + 3:.1f}" '
        f'width="{tank_w - 6}" height="{tank_h - 6:.1f}" rx="6"/></clipPath>'
    )
    parts.append(
        f'<rect x="{tank_x + 3:.1f}" y="{liquid_y:.1f}" width="{tank_w - 6}" '
        f'height="{max(liquid_h - 3, 4):.1f}" fill="url(#coolantGrad)" '
        f'clip-path="url(#tankClip)" filter="url(#glow)"/>'
    )
    parts.append(
        f'<line x1="{tank_x + 3:.1f}" y1="{liquid_y:.1f}" x2="{tank_x + tank_w - 3:.1f}" '
        f'y2="{liquid_y:.1f}" stroke="#fff3d0" stroke-width="1.2" opacity="0.8" '
        f'clip-path="url(#tankClip)"/>'
    )
    # 氣泡上升動畫
    random.seed(f"bubbles-{today_count}")
    for i in range(6):
        bx = tank_x + 10 + (i % 3) * (tank_w - 20) / 2 + random.uniform(-3, 3)
        by_start = tank_y + tank_h - 6
        by_end = liquid_y + 3
        r = round(random.uniform(1.6, 3.6), 1)
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

    # CPU 水冷頭（覆蓋在迴路右側垂直邊上），維持固定的震光綠色，不與 COOLANT TEMP 顏色連動
    cpu_cx, cpu_cy = loop_x1, loop_y0 + loop_h / 2
    cpu_color = COLOR_NEON_GREEN
    # 風扇轉速依 PUMP SPEED 連動：轉速越高，動畫週期越短（轉得越快）
    fan_dur = round(clamp(1.6 - (pump_rpm - 3500) / 500 * 0.6, 1.0, 1.6), 2)

    # B：外圍呼吸光暈（opacity 週期性脈動，模擬散熱運作中的「心跳」）
    parts.append(
        f'<rect x="{cpu_cx - 30:.1f}" y="{cpu_cy - 30:.1f}" width="60" height="60" rx="9" '
        f'fill="none" stroke="{cpu_color}" stroke-width="1.4" opacity="0.4" filter="url(#glow)">'
        f'<animate attributeName="opacity" values="0.2;0.75;0.2" dur="2.4s" repeatCount="indefinite"/>'
        f'</rect>'
    )
    parts.append(
        f'<rect x="{cpu_cx - 26:.1f}" y="{cpu_cy - 26:.1f}" width="52" height="52" rx="6" '
        f'fill="#0b0d12" stroke="{cpu_color}" stroke-width="2" filter="url(#glow)"/>'
    )
    for fin in range(5):
        fy = cpu_cy - 18 + fin * 9
        parts.append(
            f'<line x1="{cpu_cx - 19:.1f}" y1="{fy:.1f}" x2="{cpu_cx + 19:.1f}" y2="{fy:.1f}" '
            f'stroke="{cpu_color}" stroke-width="1.1" opacity="0.5"/>'
        )
    # A：中央旋轉風扇葉輪（三片弧形桓葉形狀扇葉 + 中心軸心），整組以 animateTransform 連續旋轉
    blade_len, blade_w = 13, 7
    blade_path = (
        f'M {cpu_cx:.1f},{cpu_cy:.1f} '
        f'C {cpu_cx - blade_w:.1f},{cpu_cy - blade_len * 0.4:.1f} '
        f'{cpu_cx - blade_w * 0.3:.1f},{cpu_cy - blade_len * 0.9:.1f} '
        f'{cpu_cx:.1f},{cpu_cy - blade_len:.1f} '
        f'C {cpu_cx + blade_w * 0.55:.1f},{cpu_cy - blade_len * 0.85:.1f} '
        f'{cpu_cx + blade_w * 0.6:.1f},{cpu_cy - blade_len * 0.25:.1f} '
        f'{cpu_cx:.1f},{cpu_cy:.1f} Z'
    )
    parts.append('<g>')
    parts.append(
        f'<animateTransform attributeName="transform" type="rotate" '
        f'from="0 {cpu_cx:.1f} {cpu_cy:.1f}" to="360 {cpu_cx:.1f} {cpu_cy:.1f}" '
        f'dur="{fan_dur}s" repeatCount="indefinite"/>'
    )
    for blade in range(3):
        angle = blade * 120
        parts.append(
            f'<path d="{blade_path}" transform="rotate({angle} {cpu_cx:.1f} {cpu_cy:.1f})" '
            f'fill="{cpu_color}" opacity="0.85"/>'
        )
    parts.append(
        f'<circle cx="{cpu_cx:.1f}" cy="{cpu_cy:.1f}" r="3.4" fill="#0b0d12" '
        f'stroke="{cpu_color}" stroke-width="1.4"/>'
    )
    parts.append('</g>')
    parts.append(
        f'<text x="{cpu_cx:.1f}" y="{cpu_cy - 34:.1f}" text-anchor="middle" '
        f'font-family="{FONT_STACK}" font-size="7.5" fill="{cpu_color}">CPU BLOCK</text>'
    )

    # 數據面板：兩欄式（左標籤 / 右數值），依序列出三項狀態
    label_x = x0 + 14
    value_x = x0 + 190
    data_top = diagram_top + diagram_h + 14
    status_color = COLOR_WARNING_RED if coolant_status == "OVERCLOCK" else COLOR_NEON_GREEN
    pressure_color = COLOR_WARNING_RED if pressure_status == "HIGH" else COLOR_NEON_GREEN
    rows = [
        ("PUMP SPEED:", f"{pump_rpm:,} RPM", COLOR_AMBER),
        ("COOLANT TEMP:", f"{coolant_temp}\u00b0C [{coolant_status}]", status_color),
        ("SYS PRESSURE:", f"{sys_pressure:.2f} BAR ({pressure_status})", pressure_color),
    ]
    for i, (label, value, color) in enumerate(rows):
        row_y = data_top + i * 20
        parts.append(
            f'<text x="{label_x:.1f}" y="{row_y:.1f}" font-family="{FONT_STACK}" '
            f'font-size="11" fill="#c9c9d0">{label}</text>'
        )
        parts.append(
            f'<text x="{value_x:.1f}" y="{row_y:.1f}" font-family="{FONT_STACK}" '
            f'font-size="11" font-weight="bold" fill="{color}">{value}</text>'
        )

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# 右側組件：Bug 誘捕電磁防禦塔
# ---------------------------------------------------------------------------

def build_bug_icon(cx: float, cy: float) -> str:
    """繪製一個掙扎中的黃色 Bug 向量圖標（橢圓身軀 + 亂舞的六隻腳 + 觸角）。
    F：內層 <g> 以 animateTransform 來回擺動旋轉角度，模擬觸電掙扎抖動。
    """
    return f"""<g transform="translate({cx:.1f},{cy:.1f})">
      <g>
        <animateTransform attributeName="transform" type="rotate"
          values="-12;-26;2;-20;-8;-12" dur="0.45s" repeatCount="indefinite"/>
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
      </g>
    </g>"""


def _lightning_path(x1: float, y1: float, x2: float, y2: float,
                     segments: int, jitter: float, seed: str) -> str:
    """以指定 seed 產生一條折線閃電路徑字串（供多組路徑做 flicker 動畫用）。"""
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
    return "M " + " L ".join(f"{px:.1f},{py:.1f}" for px, py in points)


def build_lightning(x1: float, y1: float, x2: float, y2: float,
                     segments: int = 6, jitter: float = 10.0,
                     color: str = COLOR_NEON_GREEN, seed: str = "bolt") -> str:
    """以多節點折線模擬尖銳閃電束，並套用強發光濾鏡。
    D：在 3 條端點相同、抖動幅度不同的路徑之間快速切換 + opacity 閃爍，
    模擬電弧持續放電、忽明忽暗的效果。
    """
    d0 = _lightning_path(x1, y1, x2, y2, segments, jitter, seed)
    d1 = _lightning_path(x1, y1, x2, y2, segments, jitter, f"{seed}-f1")
    d2 = _lightning_path(x1, y1, x2, y2, segments, jitter, f"{seed}-f2")
    d_anim = f'<animate attributeName="d" values="{d0};{d1};{d2};{d0}" dur="0.2s" repeatCount="indefinite"/>'
    op_anim = ('<animate attributeName="opacity" values="1;0.5;1;0.75;1" '
               'dur="0.15s" repeatCount="indefinite"/>')
    return (
        f'<path d="{d0}" fill="none" stroke="{color}" stroke-width="2.2" '
        f'stroke-linecap="round" stroke-linejoin="round" filter="url(#glowStrong)">'
        f'{d_anim}{op_anim}</path>'
        f'<path d="{d0}" fill="none" stroke="#ffffff" stroke-width="0.8" '
        f'stroke-linecap="round" stroke-linejoin="round" opacity="0.85">{d_anim}</path>'
    )


def compute_bugs_destroyed(today_count: int) -> int:
    """依今日 Commit 數（或自嘲式隨機數）產出消滅 Bug 統計數字。"""
    if today_count <= 0:
        return random.randint(13, 42)
    return today_count * random.randint(9, 14) + random.randint(3, 27)


def compute_threat_level(bugs_destroyed: int) -> str:
    """用自嘲式幽默包裝威脅等級：防禦塔火力全開，威脅永遠是「還好」。"""
    if bugs_destroyed > 150:
        return "ELEVATED"
    if bugs_destroyed > 60:
        return "LOW"
    return "MINIMAL"


def build_cone_tower(cx: float, base_y: float, base_w: float = 74, top_w: float = 24,
                      height: float = 92) -> Tuple[str, float]:
    """繪製精簡版電磁防禦塔塔身（類錐形結構 + 雙道琥珀警示環帶）。
    回傳 (svg片段, 塔頂座標 apex_y) 供頂端電磁球與閃電定位使用。
    """
    top_y = base_y - height
    lb, rb = (cx - base_w / 2, base_y), (cx + base_w / 2, base_y)
    lt, rt = (cx - top_w / 2, top_y), (cx + top_w / 2, top_y)

    def fmt(pts):
        return " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)

    parts = [
        f'<polygon points="{fmt([lb, rb, rt, lt])}" fill="#12161d" stroke="{COLOR_AMBER}" stroke-width="1.6"/>'
    ]
    for t in (0.32, 0.64):
        y = base_y - height * t
        half_w = (base_w / 2) * (1 - t) + (top_w / 2) * t
        stripe_h = 7
        parts.append(
            f'<rect x="{cx - half_w:.1f}" y="{y - stripe_h / 2:.1f}" '
            f'width="{2 * half_w:.1f}" height="{stripe_h}" fill="{COLOR_AMBER}"/>'
        )
    # 底座橢圓陰影，增加落地穩重感
    parts.append(
        f'<ellipse cx="{cx:.1f}" cy="{base_y + 2:.1f}" rx="{base_w / 2 + 6:.1f}" ry="4" '
        f'fill="#000000" opacity="0.35"/>'
    )
    return "\n".join(parts), top_y


def build_tesla_tower(panel: Tuple[float, float, float, float], today_count: int) -> str:
    """繪製右側 Bug 誘捕電磁防禦塔：錐形塔身 + 發光電磁球 + 左右閃電束。"""
    x0, y0, x1, y1 = panel
    cx = x0 + (x1 - x0) / 2

    # 同樣以「今天日期 + 今日 Commit 數」為種子，確保數值在同一天內保持穩定，
    # 只有 Commit 數真的變動（或跨日）時才會改變，避免高頻排程洗版 commit 紀錄。
    random.seed(f"tesla-{date.today().isoformat()}-{today_count}")
    bugs_destroyed = compute_bugs_destroyed(today_count)
    threat_level = compute_threat_level(bugs_destroyed)

    parts: List[str] = [build_panel_title(panel, "\u26a1", "EM BUG INTERCEPTOR", COLOR_NEON_GREEN)]

    diagram_top = y0 + 26
    diagram_h = 150
    base_y = diagram_top + diagram_h - 20

    cone_svg, apex_y = build_cone_tower(cx, base_y)
    parts.append(cone_svg)

    orb_cy = apex_y - 16
    # E：發光電磁球（外光暈半徑、中圈半徑、核心亮度都持續脈動，模擬蓄能中）
    parts.append(
        f'<circle cx="{cx:.1f}" cy="{orb_cy:.1f}" r="19" fill="url(#orbGlow)">'
        f'<animate attributeName="r" values="17;22;17" dur="1.8s" repeatCount="indefinite"/>'
        f'</circle>'
    )
    parts.append(
        f'<circle cx="{cx:.1f}" cy="{orb_cy:.1f}" r="10" fill="none" stroke="{COLOR_NEON_GREEN}" '
        f'stroke-width="1.2" opacity="0.8">'
        f'<animate attributeName="r" values="9;12;9" dur="1.8s" repeatCount="indefinite"/>'
        f'</circle>'
    )
    parts.append(
        f'<circle cx="{cx:.1f}" cy="{orb_cy:.1f}" r="6.5" fill="#eafffa" filter="url(#glowStrong)">'
        f'<animate attributeName="opacity" values="1;0.65;1" dur="1.2s" repeatCount="indefinite"/>'
        f'</circle>'
    )

    # 左右閃電束擊中點：與電磁球同高，直接橫向命中兩側標靶
    target_y = orb_cy + 4
    bug_cx = x0 + 22
    exc_x = x1 - 8
    parts.append(build_lightning(cx - 15, orb_cy, bug_cx + 16, target_y,
                                  segments=5, jitter=8, color=COLOR_NEON_GREEN,
                                  seed=f"bolt-left-{today_count}"))
    parts.append(build_lightning(cx + 15, orb_cy, exc_x - 40, target_y,
                                  segments=5, jitter=8, color=COLOR_NEON_GREEN,
                                  seed=f"bolt-right-{today_count}"))

    # 左側：被擊中的 Bug + 標籤
    parts.append(build_bug_icon(bug_cx, target_y))
    parts.append(
        f'<text x="{bug_cx:.1f}" y="{target_y - 20:.1f}" text-anchor="middle" '
        f'font-family="{FONT_STACK}" font-size="7.5" font-weight="bold" '
        f'fill="{COLOR_WARNING_RED}">[TARGET DETECTED]</text>'
    )

    # 右側：被擊中的例外文字（靠右對齊，附紅色虛線底線呼應參考圖）
    parts.append(
        f'<text x="{exc_x:.1f}" y="{target_y - 4:.1f}" text-anchor="end" '
        f'font-family="{FONT_STACK}" font-size="9.5" font-weight="bold" '
        f'fill="{COLOR_WARNING_RED}" filter="url(#glow)">NullPointer</text>'
    )
    text_w = 78
    parts.append(
        f'<line x1="{exc_x - text_w:.1f}" y1="{target_y + 4:.1f}" x2="{exc_x:.1f}" '
        f'y2="{target_y + 4:.1f}" stroke="{COLOR_WARNING_RED}" stroke-width="1.2" '
        f'stroke-dasharray="3 2"/>'
    )

    # 數據面板：兩欄式（左標籤 / 右數值），依序列出四項狀態
    label_x = x0 + 14
    value_x = x0 + 190
    data_top = diagram_top + diagram_h + 14
    threat_color = COLOR_WARNING_RED if threat_level == "ELEVATED" else COLOR_NEON_GREEN
    rows = [
        ("SHIELD INTEGRITY:", "ACTIVE (100%)", COLOR_NEON_GREEN),
        ("ZAP DISCHARGE:", "8.4 kV [MAX]", COLOR_AMBER),
        ("BUGS DESTROYED:", f"{bugs_destroyed} EXCEPTIONS", COLOR_AMBER),
        ("THREAT LEVEL:", threat_level, threat_color),
    ]
    for i, (label, value, color) in enumerate(rows):
        row_y = data_top + i * 18
        parts.append(
            f'<text x="{label_x:.1f}" y="{row_y:.1f}" font-family="{FONT_STACK}" '
            f'font-size="10.5" fill="#c9c9d0">{label}</text>'
        )
        parts.append(
            f'<text x="{value_x:.1f}" y="{row_y:.1f}" font-family="{FONT_STACK}" '
            f'font-size="10.5" font-weight="bold" fill="{color}">{value}</text>'
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
    parts = [
        f'<line x1="{PANEL_MID:.1f}" y1="{y0}" x2="{PANEL_MID:.1f}" y2="{y1}" '
        f'stroke="{COLOR_GRID_LINE}" stroke-width="1.5" stroke-dasharray="2 4"/>'
    ]
    parts.append(
        f'<line x1="{18}" y1="{y0}" x2="{WIDTH - 18}" y2="{y0}" stroke="{COLOR_GRID_LINE}" stroke-width="1"/>'
    )
    parts.append(
        f'<line x1="{18}" y1="{y1}" x2="{WIDTH - 18}" y2="{y1}" stroke="{COLOR_GRID_LINE}" stroke-width="1"/>'
    )
    return "\n".join(parts)


def build_header_footer(total_contributions: int) -> str:
    # 顯示台灣時區 (UTC+8)，而非 GitHub Actions 執行環境預設的 UTC
    taipei_tz = timezone(timedelta(hours=8))
    now = datetime.now(taipei_tz).strftime("%Y-%m-%d %H:%M (UTC+8)")
    parts = []
    # 頂部標語：置中顯示，並用中性白色避免與其他琴珀金文字争霸
    parts.append(
        f'<text x="{WIDTH / 2:.1f}" y="20" text-anchor="middle" font-family="{FONT_STACK}" '
        f'font-size="13" font-weight="bold" fill="#e8e8ec" letter-spacing="1">'
        f'PROJECT: Bug-Zapper &amp; Chill v1.0</text>'
    )
    parts.append(f'<circle cx="{WIDTH - 195}" cy="16" r="4" fill="{COLOR_NEON_GREEN}" filter="url(#glow)">'
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
    total = contrib_data["total"]
    today_count = contrib_data["today_count"]

    cooling_svg = build_cooling_loop(LEFT_PANEL, today_count)
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
