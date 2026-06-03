#!/usr/bin/env python3
"""Generate the MetricLens *approach* figure (paper-style method pipeline).

Depicts the core methodology — not deployment — as a left-to-right pipeline:
metric history -> seasonal-trend+AR decomposition forecast with a 95% interval
-> robust p95 peak -> SLO-constrained integer-programming rightsizing -> GCP
machine-type snap -> resize. Key formulae and a small forecast sketch are drawn
inline so the figure reads like a method overview in a paper.

Outputs:  docs/diagrams/approach.svg, docs/diagrams/approach.png
"""

from __future__ import annotations

import math
from pathlib import Path
from xml.sax.saxutils import escape

import cairosvg

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "docs" / "diagrams"
OUT_DIR.mkdir(parents=True, exist_ok=True)

BG = "#ffffff"
CARD = "#ffffff"
BORDER = "#c2c9d1"
INK = "#1f2328"
SUB = "#57606a"
ARROW = "#57606a"
ACC = "#1f77b4"
BAND = "#1f77b4"
FORMULA_BG = "#eef4fb"


def text(x, y, s, size, fill, weight="normal", anchor="start", mono=False):
    fam = "Consolas, monospace" if mono else "NanumGothic, Helvetica, Arial, sans-serif"
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" '
            f'font-weight="{weight}" text-anchor="{anchor}" '
            f'font-family="{fam}">{escape(s)}</text>')


def card(n, x, y, w, h, title, lines):
    parts = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="{CARD}" stroke="{BORDER}"/>',
        f'<circle cx="{x+20}" cy="{y+20}" r="12" fill="{ACC}"/>',
        text(x + 20, y + 24, str(n), 12, "#fff", "bold", "middle"),
        text(x + 40, y + 25, title, 12.5, INK, "bold"),
    ]
    for i, ln in enumerate(lines):
        parts.append(text(x + 14, y + 48 + i * 15, ln, 10, SUB))
    return "".join(parts)


def harrow(x1, x2, y, label=""):
    s = (f'<line x1="{x1}" y1="{y}" x2="{x2-8}" y2="{y}" stroke="{ARROW}" stroke-width="1.5"/>'
         f'<path d="M{x2},{y} L{x2-8},{y-5} L{x2-8},{y+5} Z" fill="{ARROW}"/>')
    if label:
        s += text((x1 + x2) / 2, y - 8, label, 9.5, SUB, anchor="middle")
    return s


def forecast_sketch(x, y, w, h):
    """A small history->forecast curve with a shaded 95% interval."""
    n = 28
    split = 18
    pts = []
    for i in range(n):
        t = i / (n - 1)
        val = 0.5 + 0.32 * math.sin(t * 6.0) - 0.12 * t
        pts.append((x + t * w, y + h - val * h))
    hist = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts[:split])
    fc = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts[split - 1:])
    band = []
    for i in range(split - 1, n):
        px, py = pts[i]
        band.append((px, py - 9))
    for i in range(n - 1, split - 2, -1):
        px, py = pts[i]
        band.append((px, py + 9))
    bandpts = " ".join(f"{px:.1f},{py:.1f}" for px, py in band)
    return "".join([
        f'<rect x="{x-8}" y="{y-12}" width="{w+16}" height="{h+24}" rx="6" '
        f'fill="#fff" stroke="{BORDER}"/>',
        text(x - 2, y - 16, "예측(forecast) + 95% 구간(interval)", 8.5, SUB),
        f'<polygon points="{bandpts}" fill="{BAND}" fill-opacity="0.15"/>',
        f'<polyline points="{hist}" fill="none" stroke="#111" stroke-width="1.4"/>',
        f'<polyline points="{fc}" fill="none" stroke="{ACC}" stroke-width="1.4" stroke-dasharray="4 3"/>',
    ])


def build():
    W, H = 1280, 470
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           f'<rect width="{W}" height="{H}" fill="{BG}"/>',
           text(W / 2, 40, "MetricLens 접근법: 예측에서 SLO 제약 "
                "정수계획(integer programming) 리사이징까지", 16, INK, "bold", "middle")]

    cards = [
        ("메트릭 이력", ["CPU · 메모리 · 네트워크", "시계열 (시간단위)"]),
        ("분해 + AR 보정", ["추세(trend) + 계절(seasonal)", "+ rho·잔차 → 예측(forecast)"]),
        ("강건 피크 (p95)", ["예측의 p95 통계", "(단발 스파이크 무시)"]),
        ("정수계획 최적화", ["최소 할당 탐색", "s.t. 헤드룸 (정확 해)"]),
        ("GCP 머신 타입", ["가장 근접한", "E2/N2/C2/C3 인스턴스"]),
        ("리사이즈 + 감사", ["SLO 보존", "감사 로그 영속 기록"]),
    ]
    n = len(cards)
    cw, ch, gap = 178, 96, 18
    total = n * cw + (n - 1) * gap
    x0 = (W - total) / 2
    cy = 170
    for i, (title, lines) in enumerate(cards):
        x = x0 + i * (cw + gap)
        svg.append(card(i + 1, x, cy, cw, ch, title, lines))
        if i > 0:
            svg.append(harrow(x0 + i * (cw + gap) - gap, x, cy + ch / 2))

    # Forecast sketch above card 2.
    c2x = x0 + 1 * (cw + gap)
    svg.append(forecast_sketch(c2x + 16, 70, cw - 32, 56))
    svg.append(f'<line x1="{c2x+cw/2}" y1="138" x2="{c2x+cw/2}" y2="{cy}" '
               f'stroke="{BORDER}" stroke-width="1" stroke-dasharray="3 3"/>')

    # Constraint formula callout under cards 3-4.
    fx, fy, fw, fh = x0 + 2 * (cw + gap) - 30, cy + ch + 40, 2 * cw + gap + 60, 64
    svg.append(f'<rect x="{fx}" y="{fy}" width="{fw}" height="{fh}" rx="8" '
               f'fill="{FORMULA_BG}" stroke="{ACC}" stroke-opacity="0.5"/>')
    svg.append(text(fx + fw / 2, fy + 26, "peak_load × safety_margin  ≤  "
                    "target_utilisation × allocation", 13, INK, "bold", "middle", mono=True))
    svg.append(text(fx + fw / 2, fy + 48, "전수 열거(exact enumeration)로 최소 할당 탐색 "
                    "— 실현 가능한 최소 정수 사양", 10, SUB, anchor="middle"))
    cx34 = x0 + 3 * (cw + gap) + cw / 2 - cw / 2
    svg.append(f'<line x1="{fx+fw/2}" y1="{fy}" x2="{x0+3*(cw+gap)+cw/2}" y2="{cy+ch}" '
               f'stroke="{ACC}" stroke-width="1" stroke-dasharray="3 3"/>')
    _ = cx34

    svg.append(text(W / 2, H - 16, "그림. MetricLens 방법론 — 텔레메트리에서 SLO 인지 리사이징까지의 "
                    "화이트박스(white-box)·GPU-프리 파이프라인.",
                    12, INK, "normal", "middle"))
    svg.append("</svg>")
    svg_text = "".join(svg)

    (OUT_DIR / "approach.svg").write_text(svg_text, encoding="utf-8")
    cairosvg.svg2png(bytestring=svg_text.encode("utf-8"),
                     write_to=str(OUT_DIR / "approach.png"),
                     output_width=W * 2, output_height=H * 2)
    print(f"Wrote {OUT_DIR/'approach.svg'} and approach.png")


if __name__ == "__main__":
    build()
