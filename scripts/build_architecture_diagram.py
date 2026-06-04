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

# Paper style: white fills, thin near-black lines.
BG, BAND_FILL, BAND_BORDER = "#ffffff", "#ffffff", "#16191d"
BOX_FILL, BOX_BORDER, INK, SUB = "#ffffff", "#16191d", "#16191d", "#454b52"
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
# External GCP data plane — the live source the system pulls telemetry from and
# actuates resizes against. Made explicit so ingestion is not hidden in Data.
FLEET = [
    ("googlecloud", "#4285F4", "Compute Engine", "VM inventory · setMachineType", "VM 인벤토리 · setMachineType"),
    ("googlecloud", "#4285F4", "Cloud Monitoring", "instance/cpu/utilization", "instance/cpu/utilization (CPU)"),
    ("googlecloud", "#4285F4", "Ops Agent", "memory/percent_used", "memory/percent_used (메모리)"),
]
# Cross-cutting infrastructure — kept SEPARATE from the 3 logical layers and split
# into runtime platform vs. CI/CD so the build pipeline is not shown as a 4th layer.
RUNTIME = [
    ("googlecloud", "#4285F4", "Cloud Run", "serverless · scale-to-zero", "서버리스 · scale-to-zero"),
    ("docker", "#2496ED", "Docker", "non-root images", "비루트 컨테이너 이미지"),
]
CICD = [
    ("git", "#F05032", "git push", "GitHub · main branch", "GitHub · main 브랜치"),
    ("googlecloud", "#4285F4", "Cloud Build", "lint·test·build → deploy", "린트·테스트·빌드 → 배포"),
]

TR = {
    "en": {
        "p": ("Presentation", "browser SPA on Cloud Run"),
        "b": ("Business", "layered FastAPI + dependency-free Core"),
        "d": ("Data", "managed Postgres (prod) · embedded SQLite (demo)"),
        "fleet": ("GCP managed fleet — external data plane",
                  "live CPU/memory telemetry + resize actuation"),
        "ingest": "ingest · GcpSyncService: list_time_series → persist (Metric/Host)",
        "actuate": "actuate: setMachineType",
        "infra": "Deployment infrastructure (cross-cutting)",
        "rt": ("Runtime platform", "GCP-native, scale-to-zero"),
        "ci": ("CI/CD pipeline", "Cloud Build → Cloud Run"),
        "a1": "REST / HTTPS (CORS)", "a2": "SQLAlchemy 2.0 async", "a3": "build & deploy",
        "cap": "Figure. MetricLens AI layered architecture with the live GCP data plane (Cloud Run).",
    },
    "kr": {
        "p": ("표현 계층 (Presentation)", "브라우저 SPA · Cloud Run"),
        "b": ("업무 계층 (Business)", "레이어드 FastAPI + 의존성 없는 Core"),
        "d": ("데이터 계층 (Data)", "운영 Postgres · 데모 SQLite"),
        "fleet": ("GCP 관리 플릿 — 외부 데이터 플레인",
                  "실시간 CPU/메모리 텔레메트리 + 리사이즈 실행"),
        "ingest": "수집 · GcpSyncService: list_time_series → 영속화(Metric/Host)",
        "actuate": "실행: setMachineType",
        "infra": "배포 인프라 (계층 횡단 관심사)",
        "rt": ("런타임 플랫폼", "GCP 네이티브, scale-to-zero"),
        "ci": ("CI/CD 파이프라인", "Cloud Build → Cloud Run"),
        "a1": "REST / HTTPS (CORS)", "a2": "SQLAlchemy 2.0 async", "a3": "빌드·배포",
        "cap": "그림. MetricLens AI 레이어드 아키텍처와 실시간 GCP 데이터 플레인 (Cloud Run).",
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


def _strwidth(s, size):
    """Estimate rendered width: CJK/Hangul glyphs are full-width, others ~0.52em."""
    return sum(size * (1.0 if ord(ch) >= 0x1100 else 0.52) for ch in s)


def _fit(s, maxw, size, minsize):
    """Largest font size <= ``size`` (down to ``minsize``) that fits ``maxw`` px."""
    while size > minsize and _strwidth(s, size) > maxw:
        size -= 0.5
    return size


def _text(x, y, s, size, fill, weight="normal", anchor="start"):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" '
            f'text-anchor="{anchor}" font-family="{FONT}">{escape(s)}</text>')


def block(paths, slug, color, name, role, x, y, w, h):
    parts = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{BOX_FILL}" stroke="{BOX_BORDER}"/>']
    d = paths.get(slug); lx = x + 16
    if d:
        parts.append(f'<g transform="translate({lx},{y + h / 2 - 14}) scale({28 / 24.0})"><path d="{d}" fill="{color}"/></g>')
    # Text starts at lx+40; keep a 12px right pad so nothing overruns the box edge.
    avail = w - (lx + 40 - x) - 12
    parts.append(_text(lx + 40, y + h / 2 - 4, name, _fit(name, avail, 14, 10.5), INK, "bold"))
    parts.append(_text(lx + 40, y + h / 2 + 15, role, _fit(role, avail, 11, 8.5), SUB))
    return "".join(parts)


def band(paths, label, sub, items, y, W, lang, h=104, bw=280):
    left_col = 230; area = (W - 56) - left_col; gap, bh = 26, 64
    n = len(items); total = n * bw + (n - 1) * gap; startx = left_col + (area - total) / 2
    lw = startx - 60 - 14  # label column width: never let it reach the first box
    parts = [f'<rect x="40" y="{y}" width="{W - 80}" height="{h}" rx="10" fill="{BAND_FILL}" stroke="{BAND_BORDER}"/>',
             _text(60, y + h / 2 - 3, label, _fit(label, lw, 14, 9), INK, "bold"),
             _text(60, y + h / 2 + 15, sub, _fit(sub, lw, 10, 8), SUB)]
    by = y + h / 2 - bh / 2
    for i, (slug, color, name, role_en, role_kr) in enumerate(items):
        role = role_en if lang == "en" else role_kr
        parts.append(block(paths, slug, color, name, role, startx + i * (bw + gap), by, bw, bh))
    return "".join(parts)


def arrow(x, y1, y2, label, color=INK):
    return (f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2 - 9}" stroke="{color}" stroke-width="1.4"/>'
            f'<path d="M{x - 5},{y2 - 9} L{x + 5},{y2 - 9} L{x},{y2} Z" fill="{color}"/>'
            + _text(x + 14, (y1 + y2) / 2 + 4, label, 11, SUB))


def arrow_up(x, y1, y2, label, color=INK):
    """Arrow drawn from y1 (lower) up to y2 (upper); head points up at y2."""
    return (f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2 + 9}" stroke="{color}" stroke-width="1.4"/>'
            f'<path d="M{x - 5},{y2 + 9} L{x + 5},{y2 + 9} L{x},{y2} Z" fill="{color}"/>'
            + _text(x + 14, (y1 + y2) / 2 + 4, label, 11, SUB))


def parrow(pts, label="", lx=None, ly=None, anchor="start", color=INK):
    """Orthogonal polyline arrow through waypoints; head at the final segment."""
    segs = "".join(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
                   f'stroke-width="1.4"/>'
                   for (x1, y1), (x2, y2) in zip(pts[:-1], pts[1:], strict=True))
    (px, py), (ex, ey) = pts[-2], pts[-1]
    dx, dy = ex - px, ey - py
    if abs(dx) >= abs(dy):  # horizontal final segment
        s = 1 if dx >= 0 else -1
        head = f'<path d="M{ex - 9 * s},{ey - 5} L{ex - 9 * s},{ey + 5} L{ex},{ey} Z" fill="{color}"/>'
    else:  # vertical final segment
        s = 1 if dy >= 0 else -1
        head = f'<path d="M{ex - 5},{ey - 9 * s} L{ex + 5},{ey - 9 * s} L{ex},{ey} Z" fill="{color}"/>'
    txt = _text(lx, ly, label, 11, SUB, anchor=anchor) if label and lx is not None else ""
    return segs + head + txt


def panel(paths, label, sub, items, x, y, w, h, lang):
    """A self-contained infra panel (runtime / CI/CD) — kept separate from layers."""
    parts = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{BAND_FILL}" stroke="{BAND_BORDER}"/>',
             _text(x + 18, y + 24, label, 13, INK, "bold"), _text(x + 18, y + 40, sub, 10, SUB)]
    pad, gap, bh = 18, 18, 64
    n = len(items); bw = (w - 2 * pad - (n - 1) * gap) / n; by = y + h - pad - bh
    for i, (slug, color, name, role_en, role_kr) in enumerate(items):
        role = role_en if lang == "en" else role_kr
        parts.append(block(paths, slug, color, name, role, x + pad + i * (bw + gap), by, bw, bh))
    return "".join(parts)


def build_one(paths, lang, suf):
    # 16:9 canvas so the figure drops cleanly onto a PowerPoint slide.
    T = TR[lang]; W, H = 1280, 720; cx = W / 2
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           f'<rect width="{W}" height="{H}" fill="{BG}"/>']
    # Three logical layers (the layered architecture proper), connected top-to-bottom.
    svg.append(band(paths, *T["p"], PRESENTATION, 44, W, lang, h=88)); svg.append(arrow(cx, 132, 162, T["a1"]))
    svg.append(band(paths, *T["b"], BUSINESS, 162, W, lang, h=88)); svg.append(arrow(cx, 250, 280, T["a2"]))
    svg.append(band(paths, *T["d"], DATA, 280, W, lang, h=88))
    # External GCP data plane + the live control loop, drawn explicitly so the
    # telemetry pull and resize actuation are not collapsed into the Data icon.
    svg.append(band(paths, *T["fleet"], FLEET, 424, W, lang, h=88))
    # The 56px channel between Data (ends 368) and the fleet (starts 424) holds both
    # loop arrows side by side, well apart, so neither label overlaps the other.
    svg.append(arrow_up(380, 424, 368, T["ingest"], color="#1f77b4"))   # telemetry in
    svg.append(arrow(900, 368, 424, T["actuate"], color="#d62728"))     # resize out
    # Cross-cutting deployment infrastructure — visually separated, CI/CD split out.
    svg.append(_text(40, 540, T["infra"], 12.5, INK, "bold"))
    svg.append(f'<line x1="40" y1="550" x2="{W - 40}" y2="550" stroke="{BAND_BORDER}" stroke-width="1" stroke-dasharray="4 4"/>')
    svg.append(panel(paths, *T["rt"], RUNTIME, 40, 560, 590, 128, lang))
    svg.append(panel(paths, *T["ci"], CICD, 650, 560, 590, 128, lang))
    svg.append(_text(cx, H - 14, T["cap"], 12, INK, "normal", "middle"))
    svg.append("</svg>")
    txt = "".join(svg)
    (OUT_DIR / f"architecture{suf}.svg").write_text(txt, encoding="utf-8")
    cairosvg.svg2png(bytestring=txt.encode("utf-8"), write_to=str(OUT_DIR / f"architecture{suf}.png"),
                     output_width=W * 2, output_height=H * 2)


def build():
    slugs = {s for grp in (PRESENTATION, BUSINESS, DATA, FLEET, RUNTIME, CICD) for s, *_ in grp}
    print("Fetching official OSS logos…")
    paths = {s: fetch_path(s) for s in slugs}
    build_one(paths, "en", "")
    build_one(paths, "kr", "_kr")
    print(f"Wrote architecture.png (EN) + architecture_kr.png to {OUT_DIR}")


if __name__ == "__main__":
    build()
