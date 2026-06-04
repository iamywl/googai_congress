#!/usr/bin/env python3
"""MetricLens approach figure (paper-style method pipeline), EN primary + KR _kr.

metric history -> seasonal-trend+AR forecast (95% interval) -> robust p95 peak ->
SLO-constrained integer program -> GCP machine-type snap -> resize. English is
primary (approach.png); Korean is approach_kr.png.
"""

from __future__ import annotations

import math
from pathlib import Path
from xml.sax.saxutils import escape

import cairosvg

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "docs" / "diagrams"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Paper style: white fills, thin near-black lines; blue kept only for the data sketch.
BG, CARD, BORDER = "#ffffff", "#ffffff", "#16191d"
INK, SUB, ARROW, ACC, BANDC, FORMULA_BG = "#16191d", "#454b52", "#16191d", "#1f77b4", "#1f77b4", "#ffffff"
FONT = "NanumGothic, Helvetica, Arial, sans-serif"

TR = {
    "en": {
        "title": ("MetricLens approach: forecasting to "
                  "SLO-constrained integer-programming rightsizing"),
        "cards": [
            ("Metric history", ["CPU · memory · network", "time series (hourly)"]),
            ("Decomposition + AR", ["trend + seasonal", "+ rho·residual -> forecast"]),
            ("Robust peak (p95)", ["p95 of the forecast", "(ignores transient spikes)"]),
            ("Integer program", ["smallest allocation", "s.t. headroom (exact)"]),
            ("GCP machine type", ["snap to the nearest", "E2/N2/C2/C3 instance"]),
            ("Resize + audit", ["SLO preserved", "persisted to audit log"]),
        ],
        "sketch": "forecast + 95% interval",
        "f2": "exact enumeration of the smallest feasible integer size",
        "cap": ("Figure. The MetricLens method: a white-box, GPU-free "
                "pipeline from telemetry to SLO-aware rightsizing."),
    },
    "kr": {
        "title": ("MetricLens 접근법: 예측에서 SLO 제약 "
                  "정수계획(integer programming) 리사이징까지"),
        "cards": [
            ("메트릭 이력", ["CPU · 메모리 · 네트워크", "시계열 (시간단위)"]),
            ("분해 + AR 보정", ["추세(trend) + 계절(seasonal)", "+ rho·잔차 → 예측(forecast)"]),
            ("강건 피크 (p95)", ["예측의 p95 통계", "(단발 스파이크 무시)"]),
            ("정수계획 최적화", ["최소 할당 탐색", "s.t. 헤드룸 (정확 해)"]),
            ("GCP 머신 타입", ["가장 근접한", "E2/N2/C2/C3 인스턴스"]),
            ("리사이즈 + 감사", ["SLO 보존", "감사 로그 영속 기록"]),
        ],
        "sketch": "예측(forecast) + 95% 구간(interval)",
        "f2": "전수 열거(exact enumeration)로 최소 할당 탐색 — 실현 가능한 최소 정수 사양",
        "cap": ("그림. MetricLens 방법론 — 텔레메트리에서 SLO 인지 리사이징까지의 "
                "화이트박스(white-box)·GPU-프리 파이프라인."),
    },
}


def text(x, y, s, size, fill, weight="normal", anchor="start", mono=False):
    fam = "Consolas, monospace" if mono else FONT
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" '
            f'text-anchor="{anchor}" font-family="{fam}">{escape(s)}</text>')


def _strwidth(s, size):
    """Estimate rendered width: CJK/Hangul glyphs are full-width, others ~0.52em."""
    return sum(size * (1.0 if ord(ch) >= 0x1100 else 0.52) for ch in s)


def _fit(s, maxw, size, minsize):
    """Largest font size <= ``size`` (down to ``minsize``) that fits ``maxw`` px."""
    while size > minsize and _strwidth(s, size) > maxw:
        size -= 0.5
    return size


def card(n, x, y, w, h, title, lines):
    # Vertically centre the title + lines block so taller cards do not look empty.
    block_h = 26 + len(lines) * 18
    top = y + (h - block_h) / 2
    parts = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="{CARD}" stroke="{BORDER}"/>',
             f'<circle cx="{x+22}" cy="{top+8}" r="13" fill="{ACC}"/>',
             text(x + 22, top + 12, str(n), 13, "#fff", "bold", "middle"),
             text(x + 44, top + 13, title, _fit(title, w - 58, 14, 9.5), INK, "bold")]
    for i, ln in enumerate(lines):
        parts.append(text(x + 16, top + 40 + i * 18, ln, _fit(ln, w - 28, 11.5, 8.5), SUB))
    return "".join(parts)


def harrow(x1, x2, y):
    return (f'<line x1="{x1}" y1="{y}" x2="{x2-8}" y2="{y}" stroke="{ARROW}" stroke-width="1.5"/>'
            f'<path d="M{x2},{y} L{x2-8},{y-5} L{x2-8},{y+5} Z" fill="{ARROW}"/>')


def forecast_sketch(x, y, w, h, label):
    n, split = 28, 18
    pts = [(x + (i / (n - 1)) * w, y + h - (0.5 + 0.32 * math.sin((i / (n - 1)) * 6.0) - 0.12 * (i / (n - 1))) * h)
           for i in range(n)]
    hist = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts[:split])
    fc = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts[split - 1:])
    band = [(px, py - 9) for px, py in pts[split - 1:]] + [(pts[i][0], pts[i][1] + 9) for i in range(n - 1, split - 2, -1)]
    bandpts = " ".join(f"{px:.1f},{py:.1f}" for px, py in band)
    return "".join([
        f'<rect x="{x-8}" y="{y-12}" width="{w+16}" height="{h+24}" rx="6" fill="#fff" stroke="{BORDER}"/>',
        text(x - 2, y - 16, label, 8.5, SUB),
        f'<polygon points="{bandpts}" fill="{BANDC}" fill-opacity="0.15"/>',
        f'<polyline points="{hist}" fill="none" stroke="#111" stroke-width="1.4"/>',
        f'<polyline points="{fc}" fill="none" stroke="{ACC}" stroke-width="1.4" stroke-dasharray="4 3"/>',
    ])


def build_one(lang, suf):
    # 16:9 canvas filled by enlarging each row and the fonts, with sections spread
    # evenly so the breathing room reads as layout, not dead space.
    T = TR[lang]; W, H = 1280, 720; cx = W / 2
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           f'<rect width="{W}" height="{H}" fill="{BG}"/>',
           text(cx, 60, T["title"], 18, INK, "bold", "middle")]
    cards = T["cards"]; n = len(cards); cw, ch, gap = 184, 132, 20
    x0 = (W - (n * cw + (n - 1) * gap)) / 2; cy = 350
    for i, (title, lines) in enumerate(cards):
        x = x0 + i * (cw + gap)
        svg.append(card(i + 1, x, cy, cw, ch, title, lines))
        if i > 0:
            svg.append(harrow(x0 + i * (cw + gap) - gap, x, cy + ch / 2))
    # Forecast inset above card 2, enlarged so it carries visual weight.
    c2x = x0 + (cw + gap)
    sk_w, sk_y, sk_h = cw + 36, 120, 150
    svg.append(forecast_sketch(c2x + (cw - sk_w) / 2 + 8, sk_y, sk_w - 16, sk_h, T["sketch"]))
    svg.append(f'<line x1="{c2x+cw/2}" y1="{sk_y+sk_h+12}" x2="{c2x+cw/2}" y2="{cy}" stroke="{BORDER}" stroke-width="1" stroke-dasharray="3 3"/>')
    # Wide formula callout — sized so the equation never crosses the box edge.
    fw, fh = 820, 104; fx = (W - fw) / 2; fy = cy + ch + 58
    svg.append(f'<rect x="{fx}" y="{fy}" width="{fw}" height="{fh}" rx="10" fill="{FORMULA_BG}" stroke="{ACC}" stroke-opacity="0.5"/>')
    eq = "peak_load × safety_margin  ≤  target_utilisation × allocation"
    svg.append(text(fx + fw / 2, fy + 44, eq, _fit(eq, fw - 48, 16, 10), INK, "bold", "middle", mono=True))
    svg.append(text(fx + fw / 2, fy + 74, T["f2"], _fit(T["f2"], fw - 60, 12, 9), SUB, anchor="middle"))
    svg.append(f'<line x1="{fx+fw/2}" y1="{fy}" x2="{x0+3*(cw+gap)+cw/2}" y2="{cy+ch}" stroke="{ACC}" stroke-width="1" stroke-dasharray="3 3"/>')
    svg.append(text(cx, H - 22, T["cap"], 13, INK, "normal", "middle"))
    svg.append("</svg>")
    txt = "".join(svg)
    (OUT_DIR / f"approach{suf}.svg").write_text(txt, encoding="utf-8")
    cairosvg.svg2png(bytestring=txt.encode("utf-8"), write_to=str(OUT_DIR / f"approach{suf}.png"),
                     output_width=W * 2, output_height=H * 2)


def build():
    build_one("en", "")
    build_one("kr", "_kr")
    print(f"Wrote approach.png (EN) + approach_kr.png to {OUT_DIR}")


if __name__ == "__main__":
    build()
