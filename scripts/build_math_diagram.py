#!/usr/bin/env python3
"""MetricLens computation/math pipeline figure (publication style), EN + KR _kr.

Renders the end-to-end *mathematical* computation of the system as an ordered
stage pipeline: how the forecaster turns a raw series into a point forecast and
95% interval (STL decomposition + AR(1) correction), and how the optimizer turns
the forecast peak into an SLO-safe integer allocation. Each stage card carries
the exact equation the code evaluates, so the figure doubles as a derivation.

Outputs (docs/diagrams/): method_math.png (EN) + method_math_kr.png (KR).
Usage:  python scripts/build_math_diagram.py
"""

from __future__ import annotations

import re
from pathlib import Path

import cairosvg

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "docs" / "diagrams"
OUT_DIR.mkdir(parents=True, exist_ok=True)

BG = "#ffffff"
BOX_FILL, BOX_BORDER, INK, SUB = "#ffffff", "#16191d", "#16191d", "#454b52"
ACCENT_F, ACCENT_O = "#1f77b4", "#d62728"  # forecast lane / optimizer lane
BAND = "#f4f6f8"
FONT = "NanumGothic, Helvetica, Arial, sans-serif"
MONO = "DejaVu Sans Mono, Consolas, monospace"

# --- tiny math-text renderer: supports _{..}/^{..} sub/superscripts ----------
_TOK = re.compile(r"_\{([^}]*)\}|\^\{([^}]*)\}|([^_^]+|[_^])")


def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def math(x, y, s, size, fill=INK, anchor="start", weight="normal", font=MONO):
    """Render an equation string with _{sub} / ^{sup} markup as SVG tspans."""
    spans, sh = [], round(size * 0.34, 1)
    ssz = round(size * 0.72, 1)
    for sub, sup, normal in _TOK.findall(s):
        if sub:
            # subscript span, then a zero-width span that restores the baseline
            spans.append(f'<tspan dy="{sh}" font-size="{ssz}">{_esc(sub)}</tspan>'
                         f'<tspan dy="{-sh}" font-size="{size}"></tspan>')
        elif sup:
            spans.append(f'<tspan dy="{-sh}" font-size="{ssz}">{_esc(sup)}</tspan>'
                         f'<tspan dy="{sh}" font-size="{size}"></tspan>')
        else:
            spans.append(f'<tspan>{_esc(normal)}</tspan>')
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" '
            f'text-anchor="{anchor}" font-family="{font}">{"".join(spans)}</text>')


def text(x, y, s, size, fill=INK, weight="normal", anchor="start", font=FONT):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" '
            f'text-anchor="{anchor}" font-family="{font}">{_esc(s)}</text>')


def card(x, y, w, h, n, title, eqs, accent, eqfont):
    """A stage card: numbered title bar + stacked equation lines.

    ``eqfont`` must cover every glyph in ``eqs``; for Korean cards this is the
    Hangul-capable main font (a Latin-only mono font would render tofu boxes).
    """
    p = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="{BOX_FILL}" '
         f'stroke="{BOX_BORDER}"/>',
         f'<rect x="{x}" y="{y}" width="{w}" height="26" rx="9" fill="{accent}"/>',
         f'<rect x="{x}" y="{y + 14}" width="{w}" height="12" fill="{accent}"/>',
         text(x + 11, y + 18, f"{n}. {title}", 11.5, "#ffffff", "bold")]
    ey = y + 48
    for eq in eqs:
        p.append(math(x + 12, ey, eq, 12.5, font=eqfont))
        ey += 22
    return "".join(p)


def harrow(x1, x2, y, color=INK):
    return (f'<line x1="{x1}" y1="{y}" x2="{x2 - 8}" y2="{y}" stroke="{color}" stroke-width="1.5"/>'
            f'<path d="M{x2 - 8},{y - 4} L{x2 - 8},{y + 4} L{x2},{y} Z" fill="{color}"/>')


def varrow(x, y1, y2, color=INK):
    return (f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2 - 8}" stroke="{color}" stroke-width="1.5"/>'
            f'<path d="M{x - 4},{y2 - 8} L{x + 4},{y2 - 8} L{x},{y2} Z" fill="{color}"/>')


TR = {
    "en": {
        "title": "MetricLens computation pipeline: from a raw metric series to an SLO-safe integer allocation",
        "model": "Decomposition model:",
        "laneF": "A. Forecasting  —  seasonal-trend decomposition + AR(1) residual correction  (CPU-only, stdlib)",
        "laneO": "B. Resizing  —  exact integer program over a bounded space (per resource: vCPU, memory blocks)",
        "fc_in": "input",
        "fc": [("Trend (OLS)", ["T_{t} = b.t + a", "block means y_{k},", "centres c_{k} (deseason)"]),
               ("Seasonal index", ["d_{t} = y_{t} - T_{t}", "S_{j}=mean d (t mod m=j)", "re-centred: sum S_{j}=0"]),
               ("Residual + AR(1)", ["r_{t} = d_{t} - S_{t mod m}", "rho = Sr_{t}r_{t-1} / Sr_{t}^{2}", "rho in [0, 0.95]"]),
               ("Point forecast", ["y^_{n-1+h} = T_{n-1+h}", " + S_{(n-1+h) mod m}", " + rho^{h}.r_{n-1}"]),
               ("95% interval", ["RMSE: 1-step backtest", "PI = y^ +/- 1.96.RMSE", "PICP ~ 0.93-0.98"])],
        "op": [("Robust peak", ["x = p95 of forecast", "rank = ceil(0.95.N)", "(nearest-rank, not max)"]),
               ("Load (in units)", ["L = (x/100).u_{cur}.g", "g = 1.2 (safety margin)", "u_{cur}: current units"]),
               ("Integer program", ["minimise  u", "s.t.  L <= t.u", "t=0.65, u in {1..u_cur}"]),
               ("Allocation + cost", ["u* = min(u_{cur}, ceil(L/t))", "M* = ceil(L_{m}/t).256MB", "save = avg D/cur .100%"])],
        "feed": "forecast peak feeds the optimizer",
        "out": "-> snap to GCP machine type (E2 / N2 / C2 / C3), budget-guarded resize",
        "cap": "Figure. MetricLens end-to-end computation. m = seasonal period (24 for hourly). Every equation is the exact expression evaluated in core.forecaster / core.optimizer.",
        "font_main": "DejaVu Sans",
    },
    "kr": {
        "title": "MetricLens 연산 파이프라인: 원시 메트릭 시계열에서 SLO 보장 정수 할당까지",
        "model": "분해 모델:",
        "laneF": "A. 예측  —  계절-추세 분해 + AR(1) 잔차 보정  (CPU 전용, 표준 라이브러리)",
        "laneO": "B. 리사이징  —  유계 공간 정확 정수계획 (자원별: vCPU, 메모리 블록)",
        "fc_in": "입력",
        "fc": [("추세 (OLS)", ["T_{t} = b.t + a", "블록평균 y_{k},", "중심 c_{k} (계절제거)"]),
               ("계절 지수", ["d_{t} = y_{t} - T_{t}", "S_{j}=mean d (t mod m=j)", "재중심화: sum S_{j}=0"]),
               ("잔차 + AR(1)", ["r_{t} = d_{t} - S_{t mod m}", "rho = Sr_{t}r_{t-1} / Sr_{t}^{2}", "rho in [0, 0.95]"]),
               ("점예측", ["y^_{n-1+h} = T_{n-1+h}", " + S_{(n-1+h) mod m}", " + rho^{h}.r_{n-1}"]),
               ("95% 예측구간", ["RMSE: 1-스텝 백테스트", "PI = y^ +/- 1.96.RMSE", "PICP ~ 0.93-0.98"])],
        "op": [("강건 피크", ["x = 예측의 p95", "rank = ceil(0.95.N)", "(최댓값 아닌 근접순위)"]),
               ("부하(자원단위)", ["L = (x/100).u_{cur}.g", "g = 1.2 (안전마진)", "u_{cur}: 현재 단위수"]),
               ("정수계획", ["minimise  u", "s.t.  L <= t.u", "t=0.65, u in {1..u_cur}"]),
               ("할당 + 절감", ["u* = min(u_{cur}, ceil(L/t))", "M* = ceil(L_{m}/t).256MB", "절감 = avg D/cur .100%"])],
        "feed": "예측 피크가 옵티마이저 입력",
        "out": "-> GCP 머신 타입(E2 / N2 / C2 / C3)으로 스냅, 예산 가드 리사이즈",
        "cap": "그림. MetricLens 전 과정 연산. m = 계절 주기(시간단위 24). 모든 식은 core.forecaster / core.optimizer 가 실제로 계산하는 식이다.",
        "font_main": "NanumGothic",
    },
}


def build_one(lang, suf):
    T = TR[lang]; W, H = 1180, 660; cx = W / 2
    fmain = T["font_main"]
    # Equation font must cover every glyph used. EN equations are pure ASCII, so a
    # mono font reads well; KR equations embed Hangul, so they MUST use the
    # Hangul-capable main font or every Korean word renders as tofu boxes.
    eqfont = MONO if lang == "en" else fmain
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           f'<rect width="{W}" height="{H}" fill="{BG}"/>',
           text(cx, 30, T["title"], 15, INK, "bold", "middle", fmain)]

    # Decomposition-model banner.
    svg.append(f'<rect x="40" y="44" width="{W - 80}" height="34" rx="8" fill="{BAND}" stroke="{BOX_BORDER}"/>')
    svg.append(text(56, 65, T["model"], 12, SUB, "bold", "start", fmain))
    svg.append(math(190, 66, "y_{t} = T_{t} + S_{t mod m} + r_{t}", 14.5, INK, font=eqfont))
    svg.append(text(W - 56, 65, "m = period", 11, SUB, "normal", "end", fmain))

    # --- Lane A: forecasting -------------------------------------------------
    svg.append(text(40, 104, T["laneF"], 12.5, ACCENT_F, "bold", "start", fmain))
    n, cw, gap, cy, ch = 5, 200, 24, 116, 132
    total = n * cw + (n - 1) * gap; x0 = (W - total) / 2
    for i, (title, eqs) in enumerate(T["fc"]):
        x = x0 + i * (cw + gap)
        svg.append(card(x, cy, cw, ch, i + 1, title, eqs, ACCENT_F, eqfont))
        if i:
            svg.append(harrow(x - gap, x, cy + ch / 2, ACCENT_F))

    # --- feed-through: forecast peak -> optimizer ----------------------------
    feed_y = cy + ch
    svg.append(varrow(cx, feed_y, feed_y + 40, ACCENT_O))
    svg.append(text(cx + 12, feed_y + 26, T["feed"], 11, SUB, "italic", "start", fmain))

    # --- Lane B: optimizer ---------------------------------------------------
    ly = feed_y + 64
    svg.append(text(40, ly, T["laneO"], 12.5, ACCENT_O, "bold", "start", fmain))
    n2, cw2, gap2, cy2 = 4, 254, 26, ly + 12
    total2 = n2 * cw2 + (n2 - 1) * gap2; x0b = (W - total2) / 2
    for i, (title, eqs) in enumerate(T["op"]):
        x = x0b + i * (cw2 + gap2)
        svg.append(card(x, cy2, cw2, ch, i + 6, title, eqs, ACCENT_O, eqfont))
        if i:
            svg.append(harrow(x - gap2, x, cy2 + ch / 2, ACCENT_O))

    svg.append(text(cx, cy2 + ch + 30, T["out"], 12.5, INK, "bold", "middle", fmain))
    svg.append(text(cx, H - 16, T["cap"], 10.5, SUB, "normal", "middle", fmain))
    svg.append("</svg>")
    txt = "".join(svg)
    (OUT_DIR / f"method_math{suf}.svg").write_text(txt, encoding="utf-8")
    cairosvg.svg2png(bytestring=txt.encode("utf-8"),
                     write_to=str(OUT_DIR / f"method_math{suf}.png"),
                     output_width=W * 2, output_height=H * 2)


def build():
    build_one("en", "")
    build_one("kr", "_kr")
    print(f"Wrote method_math.png (EN) + method_math_kr.png to {OUT_DIR}")


if __name__ == "__main__":
    build()
