#!/usr/bin/env python3
"""MetricLens system-architecture figure (publication style), EN primary + KR _kr.

Fetches official brand icons from Simple Icons (CC0) and composes a clean layered
block diagram. English is primary (architecture.png); Korean is architecture_kr.png.
"""

from __future__ import annotations

import re
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

import cairosvg

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "docs" / "diagrams"
OUT_DIR.mkdir(parents=True, exist_ok=True)

BG, BAND_FILL, BAND_BORDER = "#ffffff", "#f5f7f9", "#d0d7de"
BOX_FILL, BOX_BORDER, INK, SUB = "#ffffff", "#c2c9d1", "#1f2328", "#57606a"
FONT = "NanumGothic, Helvetica, Arial, sans-serif"

# Component blocks: (slug, colour, name, role_en, role_kr). Names stay English.
PRESENTATION = [
    ("react", "#149ECA", "React 19 SPA", "Vite · ECharts (Canvas)", "Vite · ECharts (Canvas)"),
    ("nginx", "#009639", "nginx", "non-root static serving", "비루트 정적 서빙"),
]
BUSINESS = [
    ("fastapi", "#009688", "FastAPI", "Controller · Service · Repository", "Controller · Service · Repository"),
    ("python", "#3776AB", "Pure Core", "forecaster · optimizer", "forecaster · optimizer"),
    ("sqlalchemy", "#D71F00", "SQLAlchemy 2.0", "async ORM", "비동기 ORM"),
]
DATA = [
    ("postgresql", "#4169E1", "PostgreSQL", "production (Cloud SQL)", "운영 (Cloud SQL)"),
    ("sqlite", "#003B57", "SQLite", "embedded demo (auto-seed)", "내장 데모 (자동 시드)"),
]
PLATFORM = [
    ("googlecloud", "#4285F4", "Cloud Run / Build", "Artifact Registry · Secret Mgr", "Artifact Registry · Secret Mgr"),
    ("docker", "#2496ED", "Docker", "non-root container images", "비루트 컨테이너 이미지"),
]

TR = {
    "en": {
        "p": ("Presentation", "browser SPA on Cloud Run"),
        "b": ("Business", "layered FastAPI + dependency-free Core"),
        "d": ("Data", "managed Postgres (prod) · embedded SQLite (demo)"),
        "pf": ("Platform & CI/CD", "GCP-native, scale-to-zero"),
        "a1": "REST / HTTPS (CORS)", "a2": "SQLAlchemy 2.0 async", "a3": "build & deploy",
        "cap": "Figure. MetricLens AI layered system architecture (GCP-native, Cloud Run).",
    },
    "kr": {
        "p": ("표현 계층 (Presentation)", "브라우저 SPA · Cloud Run"),
        "b": ("업무 계층 (Business)", "레이어드 FastAPI + 의존성 없는 Core"),
        "d": ("데이터 계층 (Data)", "운영 Postgres · 데모 SQLite"),
        "pf": ("플랫폼 · CI/CD", "GCP 네이티브, scale-to-zero"),
        "a1": "REST / HTTPS (CORS)", "a2": "SQLAlchemy 2.0 async", "a3": "빌드·배포",
        "cap": "그림. MetricLens AI 레이어드 시스템 아키텍처 (GCP 네이티브, Cloud Run).",
    },
}

_PATH_RE = re.compile(r'<path[^>]*\sd="([^"]+)"')
_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"
_SOURCES = ("https://cdn.jsdelivr.net/npm/simple-icons@13/icons/{slug}.svg",
            "https://cdn.simpleicons.org/{slug}")


def fetch_path(slug):
    for tmpl in _SOURCES:
        try:
            req = urllib.request.Request(tmpl.format(slug=slug), headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=20) as resp:
                m = _PATH_RE.search(resp.read().decode("utf-8"))
                if m:
                    return m.group(1)
        except Exception:  # noqa: BLE001
            continue
    print(f"  ! fetch failed for {slug}")
    return None


def _text(x, y, s, size, fill, weight="normal", anchor="start"):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" '
            f'text-anchor="{anchor}" font-family="{FONT}">{escape(s)}</text>')


def block(paths, slug, color, name, role, x, y, w, h):
    parts = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{BOX_FILL}" stroke="{BOX_BORDER}"/>']
    d = paths.get(slug); lx = x + 16
    if d:
        parts.append(f'<g transform="translate({lx},{y + h / 2 - 14}) scale({28 / 24.0})"><path d="{d}" fill="{color}"/></g>')
    parts.append(_text(lx + 40, y + h / 2 - 4, name, 14, INK, "bold"))
    parts.append(_text(lx + 40, y + h / 2 + 15, role, 11, SUB))
    return "".join(parts)


def band(paths, label, sub, items, y, W, lang, h=104, bw=196):
    parts = [f'<rect x="40" y="{y}" width="{W - 80}" height="{h}" rx="10" fill="{BAND_FILL}" stroke="{BAND_BORDER}"/>',
             _text(60, y + h / 2 - 3, label, 14, INK, "bold"), _text(60, y + h / 2 + 15, sub, 10, SUB)]
    left_col = 230; area = (W - 56) - left_col; gap, bh = 26, 64
    n = len(items); total = n * bw + (n - 1) * gap; startx = left_col + (area - total) / 2
    by = y + h / 2 - bh / 2
    for i, (slug, color, name, role_en, role_kr) in enumerate(items):
        role = role_en if lang == "en" else role_kr
        parts.append(block(paths, slug, color, name, role, startx + i * (bw + gap), by, bw, bh))
    return "".join(parts)


def arrow(x, y1, y2, label):
    return (f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2 - 9}" stroke="{SUB}" stroke-width="1.5"/>'
            f'<path d="M{x - 5},{y2 - 9} L{x + 5},{y2 - 9} L{x},{y2} Z" fill="{SUB}"/>'
            + _text(x + 14, (y1 + y2) / 2 + 4, label, 11, SUB))


def build_one(paths, lang, suf):
    T = TR[lang]; W, H = 1000, 720; cx = W / 2
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           f'<rect width="{W}" height="{H}" fill="{BG}"/>']
    y = 36
    svg.append(band(paths, *T["p"], PRESENTATION, y, W, lang)); svg.append(arrow(cx, y + 104, y + 150, T["a1"])); y += 150
    svg.append(band(paths, *T["b"], BUSINESS, y, W, lang)); svg.append(arrow(cx, y + 104, y + 150, T["a2"])); y += 150
    svg.append(band(paths, *T["d"], DATA, y, W, lang)); y += 150
    svg.append(arrow(cx, y + 46, y + 6, T["a3"]))
    svg.append(band(paths, *T["pf"], PLATFORM, y + 46, W, lang, bw=232))
    svg.append(_text(cx, H - 18, T["cap"], 12, INK, "normal", "middle"))
    svg.append("</svg>")
    txt = "".join(svg)
    (OUT_DIR / f"architecture{suf}.svg").write_text(txt, encoding="utf-8")
    cairosvg.svg2png(bytestring=txt.encode("utf-8"), write_to=str(OUT_DIR / f"architecture{suf}.png"),
                     output_width=W * 2, output_height=H * 2)


def build():
    slugs = {s for grp in (PRESENTATION, BUSINESS, DATA, PLATFORM) for s, *_ in grp}
    print("Fetching official OSS logos…")
    paths = {s: fetch_path(s) for s in slugs}
    build_one(paths, "en", "")
    build_one(paths, "kr", "_kr")
    print(f"Wrote architecture.png (EN) + architecture_kr.png to {OUT_DIR}")


if __name__ == "__main__":
    build()
