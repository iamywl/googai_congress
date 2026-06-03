#!/usr/bin/env python3
"""Generate the MetricLens system-architecture diagram from official OSS logos.

Fetches each technology's official brand icon from Simple Icons (CC0-licensed
SVG paths), composes a dark-themed layered architecture diagram as an SVG, and
rasterises it to PNG (for the .docx report) with cairosvg.

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

# (slug, label, brand colour) — slug is the Simple Icons identifier.
PRESENTATION = [
    ("react", "React 19", "#61DAFB"),
    ("vite", "Vite", "#646CFF"),
    ("apacheecharts", "ECharts", "#AA344D"),
    ("nginx", "nginx", "#009639"),
]
BUSINESS = [
    ("fastapi", "FastAPI", "#009688"),
    ("python", "Python", "#3776AB"),
    ("pydantic", "Pydantic", "#E92063"),
    ("sqlalchemy", "SQLAlchemy", "#D71F00"),
]
DATA = [
    ("postgresql", "PostgreSQL\n(prod / Cloud SQL)", "#4169E1"),
    ("sqlite", "SQLite\n(demo)", "#003B57"),
]
PLATFORM = [
    ("googlecloud", "Cloud Run", "#4285F4"),
    ("googlecloud", "Cloud Build (CI/CD)", "#4285F4"),
    ("googlecloud", "Artifact Registry", "#4285F4"),
    ("googlecloud", "Secret Manager", "#4285F4"),
    ("docker", "Docker", "#2496ED"),
]

_PATH_RE = re.compile(r'<path[^>]*\sd="([^"]+)"')


_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"
_SOURCES = (
    "https://cdn.jsdelivr.net/npm/simple-icons@13/icons/{slug}.svg",
    "https://cdn.simpleicons.org/{slug}",
)


def fetch_path(slug: str) -> str | None:
    """Return the single SVG path 'd' for a Simple Icons slug, or None."""
    for tmpl in _SOURCES:
        url = tmpl.format(slug=slug)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=20) as resp:
                svg = resp.read().decode("utf-8")
        except Exception:  # noqa: BLE001 - try next source
            continue
        m = _PATH_RE.search(svg)
        if m:
            return m.group(1)
    print(f"  ! fetch failed for {slug}")
    return None


def icon(paths: dict, slug: str, color: str, x: float, y: float, size: float) -> str:
    """A white rounded chip with the brand-coloured logo centred inside."""
    chip = (
        f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="10" '
        f'fill="#ffffff" stroke="#30363d"/>'
    )
    d = paths.get(slug)
    if not d:
        return chip
    pad = size * 0.22
    scale = (size - 2 * pad) / 24.0
    return (
        chip
        + f'<g transform="translate({x + pad},{y + pad}) scale({scale})">'
        + f'<path d="{d}" fill="{color}"/></g>'
    )


def card(paths, slug, label, color, cx, top, size=46) -> str:
    """A logo chip with a (possibly multi-line) label centred under it."""
    x = cx - size / 2
    parts = [icon(paths, slug, color, x, top, size)]
    lines = label.split("\n")
    for i, line in enumerate(lines):
        fs = 12 if i == 0 else 10
        fill = "#c9d1d9" if i == 0 else "#8b949e"
        ty = top + size + 16 + i * 13
        parts.append(
            f'<text x="{cx}" y="{ty}" text-anchor="middle" '
            f'font-size="{fs}" fill="{fill}" '
            f'font-family="Segoe UI, system-ui, sans-serif">{escape(line)}</text>'
        )
    return "".join(parts)


def band(paths, title, subtitle, items, y, height, width, color="#4f9cff") -> str:
    """A tier band: titled rounded rect with evenly-spaced logo cards."""
    parts = [
        f'<rect x="40" y="{y}" width="{width - 80}" height="{height}" rx="14" '
        f'fill="#161b22" stroke="{color}" stroke-opacity="0.5"/>',
        f'<text x="60" y="{y + 26}" font-size="14" font-weight="700" fill="{color}" '
        f'font-family="Segoe UI, system-ui, sans-serif">{escape(title)}</text>',
        f'<text x="60" y="{y + 44}" font-size="11" fill="#8b949e" '
        f'font-family="Segoe UI, system-ui, sans-serif">{escape(subtitle)}</text>',
    ]
    n = len(items)
    start = 150
    span = width - 300
    step = span / max(1, n - 1) if n > 1 else 0
    card_top = y + height / 2 - 18
    for i, (slug, label, c) in enumerate(items):
        cx = start + (step * i if n > 1 else span / 2)
        parts.append(card(paths, slug, label, c, cx, card_top))
    return "".join(parts)


def arrow(x, y1, y2) -> str:
    return (
        f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2 - 8}" stroke="#4f9cff" '
        f'stroke-width="2"/>'
        f'<path d="M{x - 5},{y2 - 8} L{x + 5},{y2 - 8} L{x},{y2} Z" fill="#4f9cff"/>'
    )


def build() -> None:
    slugs = {s for grp in (PRESENTATION, BUSINESS, DATA, PLATFORM) for s, _, _ in grp}
    print("Fetching official OSS logos…")
    paths = {s: fetch_path(s) for s in slugs}
    ok = sum(v is not None for v in paths.values())
    print(f"  {ok}/{len(slugs)} logos fetched")

    W, H = 1000, 760
    cx = W / 2
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}">',
        f'<rect width="{W}" height="{H}" fill="#0d1117"/>',
        f'<text x="{cx}" y="44" text-anchor="middle" font-size="22" '
        f'font-weight="700" fill="#f0f6fc" '
        f'font-family="Segoe UI, system-ui, sans-serif">'
        f'MetricLens AI — System Architecture</text>',
    ]
    svg.append(band(paths, "Presentation Tier", "Browser SPA → nginx (non-root) on Cloud Run",
                    PRESENTATION, 70, 130, W))
    svg.append(arrow(cx, 200, 230))
    svg.append(band(paths, "Business Tier", "Layered API: Controller → Service → Repository + pure Core (forecaster · optimizer)",
                    BUSINESS, 230, 130, W))
    svg.append(arrow(cx, 360, 390))
    svg.append(band(paths, "Data Tier", "SQLAlchemy 2.0 async — managed Postgres in prod, embedded SQLite for the demo",
                    DATA, 390, 130, W))
    svg.append(band(paths, "Platform & CI/CD", "GCP-native: Cloud Build pipeline → Artifact Registry → Cloud Run; secrets via Secret Manager",
                    PLATFORM, 540, 150, W, color="#3fb950"))
    svg.append("</svg>")
    svg_text = "".join(svg)

    (OUT_DIR / "architecture.svg").write_text(svg_text, encoding="utf-8")
    cairosvg.svg2png(
        bytestring=svg_text.encode("utf-8"),
        write_to=str(OUT_DIR / "architecture.png"),
        output_width=W * 2,  # 2× for a crisp raster in the report
        output_height=H * 2,
    )
    print(f"Wrote {OUT_DIR/'architecture.svg'} and architecture.png")


if __name__ == "__main__":
    build()
