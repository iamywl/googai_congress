#!/usr/bin/env python3
"""Generate the MetricLens system-architecture figure (publication style).

Fetches each technology's official brand icon from Simple Icons (CC0-licensed
SVG paths) and composes a clean, paper-figure-style layered block diagram on a
white background — labelled functional blocks, thin borders, and annotated
data-flow arrows — then rasterises it to PNG with cairosvg for the .docx report.

Usage:
    python scripts/build_architecture_diagram.py
Outputs:
    docs/diagrams/architecture.svg
    docs/diagrams/architecture.png
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

# Palette — restrained, academic.
BG = "#ffffff"
BAND_FILL = "#f5f7f9"
BAND_BORDER = "#d0d7de"
BOX_FILL = "#ffffff"
BOX_BORDER = "#c2c9d1"
INK = "#1f2328"        # primary text
SUB = "#57606a"        # secondary text / arrows

# Each block: (slug, brand colour, name, role).
PRESENTATION = [
    ("react", "#149ECA", "React 19 SPA", "Vite · ECharts (Canvas)"),
    ("nginx", "#009639", "nginx", "non-root static serving"),
]
BUSINESS = [
    ("fastapi", "#009688", "FastAPI", "Controller · Service · Repository"),
    ("python", "#3776AB", "Pure Core", "forecaster · optimizer"),
    ("sqlalchemy", "#D71F00", "SQLAlchemy 2.0", "async ORM"),
]
DATA = [
    ("postgresql", "#4169E1", "PostgreSQL", "production (Cloud SQL)"),
    ("sqlite", "#003B57", "SQLite", "embedded demo (auto-seed)"),
]
PLATFORM = [
    ("googlecloud", "#4285F4", "Cloud Run / Build", "Artifact Registry · Secret Mgr"),
    ("docker", "#2496ED", "Docker", "non-root container images"),
]

_PATH_RE = re.compile(r'<path[^>]*\sd="([^"]+)"')
_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"
_SOURCES = (
    "https://cdn.jsdelivr.net/npm/simple-icons@13/icons/{slug}.svg",
    "https://cdn.simpleicons.org/{slug}",
)


def fetch_path(slug: str) -> str | None:
    for tmpl in _SOURCES:
        try:
            req = urllib.request.Request(tmpl.format(slug=slug), headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=20) as resp:
                svg = resp.read().decode("utf-8")
        except Exception:  # noqa: BLE001 - try next source
            continue
        m = _PATH_RE.search(svg)
        if m:
            return m.group(1)
    print(f"  ! fetch failed for {slug}")
    return None


def _text(x, y, s, size, fill, weight="normal", anchor="start"):
    return (
        f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" '
        f'font-weight="{weight}" text-anchor="{anchor}" '
        f'font-family="Helvetica, Arial, sans-serif">{escape(s)}</text>'
    )


def block(paths, slug, color, name, role, x, y, w, h) -> str:
    """A white component box: brand logo on the left, name + role text."""
    parts = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" '
        f'fill="{BOX_FILL}" stroke="{BOX_BORDER}"/>'
    ]
    d = paths.get(slug)
    lx = x + 16
    if d:
        size = 28
        ly = y + h / 2 - size / 2
        scale = size / 24.0
        parts.append(
            f'<g transform="translate({lx},{ly}) scale({scale})">'
            f'<path d="{d}" fill="{color}"/></g>'
        )
    tx = lx + 40
    parts.append(_text(tx, y + h / 2 - 4, name, 14, INK, "bold"))
    parts.append(_text(tx, y + h / 2 + 15, role, 11, SUB))
    return "".join(parts)


def band(paths, label, sub, items, y, W, h=104, bw=196) -> str:
    parts = [
        f'<rect x="40" y="{y}" width="{W - 80}" height="{h}" rx="10" '
        f'fill="{BAND_FILL}" stroke="{BAND_BORDER}"/>',
        _text(60, y + h / 2 - 3, label, 14, INK, "bold"),
        _text(60, y + h / 2 + 15, sub, 10, SUB),
    ]
    left_col = 230
    area = (W - 56) - left_col
    gap, bh = 26, 64
    n = len(items)
    total = n * bw + (n - 1) * gap
    startx = left_col + (area - total) / 2
    by = y + h / 2 - bh / 2
    for i, (slug, color, name, role) in enumerate(items):
        parts.append(block(paths, slug, color, name, role,
                            startx + i * (bw + gap), by, bw, bh))
    return "".join(parts)


def arrow(x, y1, y2, label) -> str:
    return (
        f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2 - 9}" stroke="{SUB}" stroke-width="1.5"/>'
        f'<path d="M{x - 5},{y2 - 9} L{x + 5},{y2 - 9} L{x},{y2} Z" fill="{SUB}"/>'
        + _text(x + 14, (y1 + y2) / 2 + 4, label, 11, SUB)
    )


def build() -> None:
    slugs = {s for grp in (PRESENTATION, BUSINESS, DATA, PLATFORM) for s, *_ in grp}
    print("Fetching official OSS logos…")
    paths = {s: fetch_path(s) for s in slugs}
    print(f"  {sum(v is not None for v in paths.values())}/{len(slugs)} fetched")

    W, H = 1000, 720
    cx = W / 2
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}">',
        f'<rect width="{W}" height="{H}" fill="{BG}"/>',
    ]
    y = 36
    svg.append(band(paths, "Presentation", "browser SPA on Cloud Run", PRESENTATION, y, W))
    svg.append(arrow(cx, y + 104, y + 150, "REST / HTTPS (CORS)"))
    y += 150
    svg.append(band(paths, "Business", "layered FastAPI + dependency-free Core", BUSINESS, y, W))
    svg.append(arrow(cx, y + 104, y + 150, "SQLAlchemy 2.0 async"))
    y += 150
    svg.append(band(paths, "Data", "managed Postgres (prod) · embedded SQLite (demo)", DATA, y, W))
    y += 150
    svg.append(arrow(cx, y + 46, y + 6, "build & deploy"))
    svg.append(band(paths, "Platform & CI/CD", "GCP-native, scale-to-zero", PLATFORM, y + 46, W, bw=232))

    # Figure caption (paper style).
    svg.append(_text(cx, H - 18,
                     "Figure 1: MetricLens AI — layered system architecture "
                     "(GCP-native, Cloud Run).", 12, INK, "normal", "middle"))
    svg.append("</svg>")
    svg_text = "".join(svg)

    (OUT_DIR / "architecture.svg").write_text(svg_text, encoding="utf-8")
    cairosvg.svg2png(
        bytestring=svg_text.encode("utf-8"),
        write_to=str(OUT_DIR / "architecture.png"),
        output_width=W * 2, output_height=H * 2,
    )
    print(f"Wrote {OUT_DIR/'architecture.svg'} and architecture.png")


if __name__ == "__main__":
    build()
