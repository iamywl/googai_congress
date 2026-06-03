#!/usr/bin/env python3
"""Generate the MetricLens runtime & CI/CD operation diagram (publication style).

Visualises *how the solution actually runs*: the Cloud Build CI/CD pipeline that
ships container images to Cloud Run, the request path through the serverless
frontend/backend, and the real-fleet data flow (the backend reading instance
metrics from Cloud Monitoring and resizing real VMs via the Compute Engine API).
Official OSS/GCP brand logos (Simple Icons, CC0) are fetched and composed into a
clean SVG, then rasterised to PNG with cairosvg.

Outputs:  docs/diagrams/runtime.svg, docs/diagrams/runtime.png
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

BG = "#ffffff"
BAND = "#f5f7f9"
BAND_BORDER = "#d0d7de"
BOX_BORDER = "#c2c9d1"
INK = "#1f2328"
SUB = "#57606a"
ARROW = "#57606a"
G = "#4285F4"  # Google Cloud blue

_PATH_RE = re.compile(r'<path[^>]*\sd="([^"]+)"')
_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"
_SRC = (
    "https://cdn.jsdelivr.net/npm/simple-icons@13/icons/{slug}.svg",
    "https://cdn.simpleicons.org/{slug}",
)


def fetch(slug: str) -> str | None:
    for t in _SRC:
        try:
            req = urllib.request.Request(t.format(slug=slug), headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=20) as r:
                m = _PATH_RE.search(r.read().decode("utf-8"))
                if m:
                    return m.group(1)
        except Exception:  # noqa: BLE001
            continue
    print(f"  ! fetch failed {slug}")
    return None


def text(x, y, s, size, fill, weight="normal", anchor="start"):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" '
            f'font-weight="{weight}" text-anchor="{anchor}" '
            f'font-family="Helvetica, Arial, sans-serif">{escape(s)}</text>')


def box(paths, x, y, w, h, slug, title, sub, color=G):
    parts = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" '
             f'fill="#ffffff" stroke="{BOX_BORDER}"/>']
    tx = x + 14
    d = paths.get(slug) if slug else None
    if d:
        size = 26
        ly = y + h / 2 - size / 2
        parts.append(f'<g transform="translate({tx},{ly}) scale({size/24.0})">'
                     f'<path d="{d}" fill="{color}"/></g>')
        tx += 36
    parts.append(text(tx, y + h / 2 - 3, title, 13, INK, "bold"))
    parts.append(text(tx, y + h / 2 + 15, sub, 10.5, SUB))
    return "".join(parts), (x, y, w, h)


def arrow(x1, y1, x2, y2, label="", lx=None, ly=None):
    import math
    ang = math.atan2(y2 - y1, x2 - x1)
    ah = 7
    bx, by = x2 - ah * math.cos(ang), y2 - ah * math.sin(ang)
    p1 = (bx - ah * math.cos(ang - 0.5), by - ah * math.sin(ang - 0.5))
    p2 = (bx - ah * math.cos(ang + 0.5), by - ah * math.sin(ang + 0.5))
    s = (f'<line x1="{x1}" y1="{y1}" x2="{bx:.1f}" y2="{by:.1f}" stroke="{ARROW}" stroke-width="1.5"/>'
         f'<path d="M{x2:.1f},{y2:.1f} L{p1[0]:.1f},{p1[1]:.1f} L{p2[0]:.1f},{p2[1]:.1f} Z" fill="{ARROW}"/>')
    if label:
        if lx is None:
            lx = (x1 + x2) / 2
        if ly is None:
            ly = (y1 + y2) / 2 - 5
        s += text(lx, ly, label, 10.5, SUB, anchor="middle")
    return s


def band(x, y, w, h, label, sub):
    return ("".join([
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{BAND}" stroke="{BAND_BORDER}"/>',
        text(x + 16, y + 22, label, 13, INK, "bold"),
        text(x + 16, y + 39, sub, 10, SUB),
    ]))


def build():
    slugs = {"git", "googlecloud", "docker"}
    print("Fetching logos…")
    paths = {s: fetch(s) for s in slugs}

    W, H = 1140, 600
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           f'<rect width="{W}" height="{H}" fill="{BG}"/>']

    bw, bh = 188, 58
    # ---- Band 1: CI/CD ----
    svg.append(band(30, 40, W - 60, 110, "CI/CD pipeline (Cloud Build to Cloud Run)",
                    "git push -> lint -> test -> build image -> deploy -> health check"))
    y1 = 78
    b_dev, r_dev = box(paths, 50, y1, 150, bh, "git", "Developer", "git push")
    b_cb, r_cb = box(paths, 270, y1, 230, bh, "googlecloud", "Cloud Build", "lint·test·build·deploy")
    b_ar, r_ar = box(paths, 560, y1, 180, bh, "googlecloud", "Artifact Registry", "container images")
    b_cr, r_cr = box(paths, 800, y1, 190, bh, "googlecloud", "Cloud Run", "scale-to-zero")
    svg += [b_dev, b_cb, b_ar, b_cr]
    svg.append(arrow(200, y1 + bh / 2, 270, y1 + bh / 2, "trigger"))
    svg.append(arrow(500, y1 + bh / 2, 560, y1 + bh / 2, "image"))
    svg.append(arrow(740, y1 + bh / 2, 800, y1 + bh / 2, "deploy"))

    # ---- Band 2: Runtime serving ----
    svg.append(band(30, 190, W - 60, 110, "Runtime serving (serverless)",
                    "browser -> frontend -> backend; secrets from Secret Manager"))
    y2 = 228
    b_br, _ = box(paths, 50, y2, 150, bh, None, "Browser", "React SPA")
    b_fe, _ = box(paths, 270, y2, 190, bh, "googlecloud", "Frontend", "Cloud Run · nginx")
    b_be, r_be = box(paths, 520, y2, 190, bh, "googlecloud", "Backend", "FastAPI · Cloud Run")
    b_sm, _ = box(paths, 800, y2, 190, bh, "googlecloud", "Secret Manager", "DB DSN / secrets")
    svg += [b_br, b_fe, b_be, b_sm]
    svg.append(arrow(200, y2 + bh / 2, 270, y2 + bh / 2, "HTTPS"))
    svg.append(arrow(460, y2 + bh / 2, 520, y2 + bh / 2, "REST"))
    svg.append(arrow(710, y2 + bh / 2, 800, y2 + bh / 2, "secrets"))

    # ---- Band 3: real fleet monitoring + resize ----
    svg.append(band(30, 340, W - 60, 220, "Real-fleet monitoring & resize (Cloud Monitoring + Compute Engine)",
                    "backend reads live CPU/memory and resizes real VMs within the budget guard"))
    b_mon, _ = box(paths, 120, 410, 220, bh, "googlecloud", "Cloud Monitoring", "CPU + memory")
    b_ce, _ = box(paths, 470, 410, 230, bh, "googlecloud", "Compute Engine API", "setMachineType")
    b_fleet, _ = box(paths, 760, 410, 320, 70, None, "Real fleet · ml-web/api/batch/idle",
                     "e2-small · load generator + Ops Agent")
    svg += [b_mon, b_ce, b_fleet]

    be_cx, be_by = 520 + 95, y2 + bh  # backend bottom-center
    svg.append(arrow(be_cx, be_by, 230, 410, "read CPU/mem"))
    svg.append(arrow(be_cx + 40, be_by, 585, 410, "resize (budget-guarded)"))
    svg.append(arrow(585, 468, 760, 455, "stop→change→start"))
    svg.append(arrow(760, 460, 340, 455, "push metrics (Ops Agent)", lx=560, ly=520))

    svg.append(text(W / 2, H - 16,
                    "Figure. MetricLens runtime & CI/CD operation (GCP-native serverless).",
                    12, INK, "normal", "middle"))
    svg.append("</svg>")
    svg_text = "".join(svg)

    (OUT_DIR / "runtime.svg").write_text(svg_text, encoding="utf-8")
    cairosvg.svg2png(bytestring=svg_text.encode("utf-8"),
                     write_to=str(OUT_DIR / "runtime.png"),
                     output_width=W * 2, output_height=H * 2)
    print(f"Wrote {OUT_DIR/'runtime.svg'} and runtime.png")


if __name__ == "__main__":
    build()
