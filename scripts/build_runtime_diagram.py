#!/usr/bin/env python3
"""MetricLens runtime & CI/CD operation diagram, EN primary + KR _kr.

Visualises how the solution runs: Cloud Build CI/CD -> Cloud Run, serverless
serving, and the real-fleet data flow (Cloud Monitoring read + Compute Engine
resize). English is primary (runtime.png); Korean is runtime_kr.png.
"""

from __future__ import annotations

import math
import re
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

import cairosvg

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "docs" / "diagrams"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Paper style: white fills, thin near-black lines.
BG, BAND, BAND_BORDER, BOX_BORDER = "#ffffff", "#ffffff", "#16191d", "#16191d"
INK, SUB, ARROW, G = "#16191d", "#454b52", "#16191d", "#4285F4"
FONT = "NanumGothic, Helvetica, Arial, sans-serif"

_PATH_RE = re.compile(r'<path[^>]*\sd="([^"]+)"')
_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"
_SRC = ("https://cdn.jsdelivr.net/npm/simple-icons@13/icons/{slug}.svg",
        "https://cdn.simpleicons.org/{slug}")

# (key) -> (en, kr). Boxes/bands/arrows that differ by language.
TR = {
    "en": {
        "b1t": "CI/CD pipeline (Cloud Build to Cloud Run)",
        "b1s": "git push -> lint -> test -> build image -> deploy -> health check",
        "dev": "Developer", "build_sub": "lint·test·build·deploy", "ar_sub": "container images",
        "b2t": "Runtime serving (serverless)",
        "b2s": "browser -> frontend -> backend; secrets from Secret Manager",
        "browser": "Browser", "frontend": "Frontend", "backend": "Backend", "sm_sub": "DB DSN / secrets",
        "b3t": "Real-fleet monitoring & resize (Cloud Monitoring + Compute Engine)",
        "b3s": "backend reads live CPU/memory and resizes real VMs within the budget guard",
        "mon_sub": "CPU + memory", "fleet": "Real fleet · ml-web/api/batch/idle",
        "fleet_sub": "e2-small · load generator + Ops Agent",
        "trigger": "trigger", "image": "image", "deploy": "deploy", "secrets": "secrets",
        "read": "read CPU/mem", "resize": "resize (budget-guarded)",
        "scs": "stop->change->start", "push": "push metrics (Ops Agent)",
        "cap": "Figure. MetricLens runtime & CI/CD operation (GCP-native serverless).",
    },
    "kr": {
        "b1t": "CI/CD 파이프라인 (Cloud Build → Cloud Run)",
        "b1s": "git push → 린트 → 테스트 → 이미지 빌드 → 배포 → 헬스 체크",
        "dev": "개발자(Developer)", "build_sub": "린트·테스트·빌드·배포", "ar_sub": "컨테이너 이미지",
        "b2t": "런타임 서빙 (서버리스)",
        "b2s": "브라우저 → 프론트엔드 → 백엔드, 비밀값은 Secret Manager",
        "browser": "브라우저(Browser)", "frontend": "프론트엔드", "backend": "백엔드", "sm_sub": "DB DSN / 비밀값",
        "b3t": "실제 플릿 모니터링 · 리사이즈 (Cloud Monitoring + Compute Engine)",
        "b3s": "백엔드가 실측 CPU/메모리를 읽고, 예산 한도 내에서 실제 VM을 리사이즈",
        "mon_sub": "CPU + 메모리", "fleet": "실제 플릿 · ml-web/api/batch/idle",
        "fleet_sub": "e2-small · 부하 생성기 + Ops Agent",
        "trigger": "트리거", "image": "이미지", "deploy": "배포", "secrets": "비밀값",
        "read": "CPU/메모리 조회", "resize": "리사이즈 (예산 가드)",
        "scs": "stop→change→start", "push": "메트릭 전송 (Ops Agent)",
        "cap": "그림. MetricLens 런타임 · CI/CD 구동 방식 (GCP 네이티브 서버리스).",
    },
}


def fetch(slug):
    for t in _SRC:
        try:
            req = urllib.request.Request(t.format(slug=slug), headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=20) as r:
                m = _PATH_RE.search(r.read().decode("utf-8"))
                if m:
                    return m.group(1)
        except Exception:  # noqa: BLE001
            continue
    return None


def text(x, y, s, size, fill, weight="normal", anchor="start"):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" '
            f'text-anchor="{anchor}" font-family="{FONT}">{escape(s)}</text>')


def _strwidth(s, size):
    """Estimate rendered width: CJK/Hangul glyphs are full-width, others ~0.52em."""
    return sum(size * (1.0 if ord(ch) >= 0x1100 else 0.52) for ch in s)


def _fit(s, maxw, size, minsize):
    """Largest font size <= ``size`` (down to ``minsize``) that fits ``maxw`` px."""
    while size > minsize and _strwidth(s, size) > maxw:
        size -= 0.5
    return size


def box(paths, x, y, w, h, slug, title, sub):
    parts = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="#fff" stroke="{BOX_BORDER}"/>']
    tx = x + 14; d = paths.get(slug) if slug else None
    if d:
        parts.append(f'<g transform="translate({tx},{y + h / 2 - 13}) scale({26 / 24.0})"><path d="{d}" fill="{G}"/></g>')
        tx += 36
    avail = (x + w) - tx - 10  # keep a right pad so text never crosses the border
    parts.append(text(tx, y + h / 2 - 3, title, _fit(title, avail, 13, 9), INK, "bold"))
    parts.append(text(tx, y + h / 2 + 15, sub, _fit(sub, avail, 10.5, 8), SUB))
    return "".join(parts)


def arrow(x1, y1, x2, y2, label="", lx=None, ly=None):
    ang = math.atan2(y2 - y1, x2 - x1); ah = 7
    bx, by = x2 - ah * math.cos(ang), y2 - ah * math.sin(ang)
    p1 = (bx - ah * math.cos(ang - 0.5), by - ah * math.sin(ang - 0.5))
    p2 = (bx - ah * math.cos(ang + 0.5), by - ah * math.sin(ang + 0.5))
    s = (f'<line x1="{x1}" y1="{y1}" x2="{bx:.1f}" y2="{by:.1f}" stroke="{ARROW}" stroke-width="1.5"/>'
         f'<path d="M{x2:.1f},{y2:.1f} L{p1[0]:.1f},{p1[1]:.1f} L{p2[0]:.1f},{p2[1]:.1f} Z" fill="{ARROW}"/>')
    if label:
        s += text(lx if lx is not None else (x1 + x2) / 2, ly if ly is not None else (y1 + y2) / 2 - 5,
                  label, 10.5, SUB, anchor="middle")
    return s


def parrow(pts, label="", lx=None, ly=None, anchor="middle"):
    """Orthogonal polyline arrow through waypoints; arrowhead at the last point.

    Routes elbows so flows never cross — used for the real-fleet control loop.
    """
    ah = 7
    (x1, y1), (x2, y2) = pts[-2], pts[-1]
    ang = math.atan2(y2 - y1, x2 - x1)
    ex, ey = x2 - ah * math.cos(ang), y2 - ah * math.sin(ang)
    seq = pts[:-1] + [(ex, ey)]
    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in seq)
    p1 = (x2 - ah * math.cos(ang - 0.5), y2 - ah * math.sin(ang - 0.5))
    p2 = (x2 - ah * math.cos(ang + 0.5), y2 - ah * math.sin(ang + 0.5))
    s = (f'<path d="{d}" fill="none" stroke="{ARROW}" stroke-width="1.5"/>'
         f'<path d="M{x2:.1f},{y2:.1f} L{p1[0]:.1f},{p1[1]:.1f} L{p2[0]:.1f},{p2[1]:.1f} Z" fill="{ARROW}"/>')
    if label:
        s += text(lx, ly, label, 10.5, SUB, anchor=anchor)
    return s


def band(x, y, w, h, label, sub):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{BAND}" stroke="{BAND_BORDER}"/>'
            + text(x + 16, y + 22, label, 13, INK, "bold") + text(x + 16, y + 39, sub, 10, SUB))


def build_one(paths, lang, suf):
    T = TR[lang]; W, H = 1140, 620
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           f'<rect width="{W}" height="{H}" fill="{BG}"/>']
    bh = 58
    svg.append(band(30, 40, W - 60, 110, T["b1t"], T["b1s"]))
    y1 = 86
    svg += [box(paths, 50, y1, 150, bh, "git", T["dev"], "git push"),
            box(paths, 270, y1, 230, bh, "googlecloud", "Cloud Build", T["build_sub"]),
            box(paths, 560, y1, 180, bh, "googlecloud", "Artifact Registry", T["ar_sub"]),
            box(paths, 800, y1, 190, bh, "googlecloud", "Cloud Run", "scale-to-zero")]
    svg += [arrow(200, y1 + bh / 2, 270, y1 + bh / 2, T["trigger"]),
            arrow(500, y1 + bh / 2, 560, y1 + bh / 2, T["image"]),
            arrow(740, y1 + bh / 2, 800, y1 + bh / 2, T["deploy"])]

    svg.append(band(30, 190, W - 60, 110, T["b2t"], T["b2s"]))
    y2 = 236
    svg += [box(paths, 50, y2, 150, bh, None, T["browser"], "React SPA"),
            box(paths, 270, y2, 190, bh, "googlecloud", T["frontend"], "Cloud Run · nginx"),
            box(paths, 520, y2, 190, bh, "googlecloud", T["backend"], "FastAPI · Cloud Run"),
            box(paths, 800, y2, 190, bh, "googlecloud", "Secret Manager", T["sm_sub"])]
    svg += [arrow(200, y2 + bh / 2, 270, y2 + bh / 2, "HTTPS"),
            arrow(460, y2 + bh / 2, 520, y2 + bh / 2, "REST"),
            arrow(710, y2 + bh / 2, 800, y2 + bh / 2, T["secrets"])]

    svg.append(band(30, 340, W - 60, 240, T["b3t"], T["b3s"]))
    # Clean orthogonal control loop (no crossings): backend reads Monitoring and
    # resizes via Compute Engine; Compute Engine drives the fleet; the fleet pushes
    # metrics back to Monitoring along a separate bottom rail.
    mon_x, mon_y, mon_w, mon_h = 80, 418, 210, 56
    ce_x, ce_y, ce_w, ce_h = 470, 418, 230, 56
    fl_x, fl_y, fl_w, fl_h = 820, 418, 270, 68
    svg += [box(paths, mon_x, mon_y, mon_w, mon_h, "googlecloud", "Cloud Monitoring", T["mon_sub"]),
            box(paths, ce_x, ce_y, ce_w, ce_h, "googlecloud", "Compute Engine API", "setMachineType"),
            box(paths, fl_x, fl_y, fl_w, fl_h, None, T["fleet"], T["fleet_sub"])]
    be_b = y2 + bh        # backend box bottom
    mon_cx = mon_x + mon_w / 2     # 185
    read_y, push_y = 402, 540
    svg += [
        # backend -> Compute Engine API (resize), straight down
        parrow([(615, be_b), (615, ce_y - 4)], T["resize"], lx=625, ly=352, anchor="start"),
        # backend -> Cloud Monitoring (read), elbow down-left into box top
        parrow([(560, be_b), (560, read_y), (mon_cx, read_y), (mon_cx, mon_y - 4)],
               T["read"], lx=378, ly=read_y - 6),
        # Compute Engine API -> fleet (stop/change/start), straight right
        parrow([(ce_x + ce_w, ce_y + ce_h / 2), (fl_x - 4, ce_y + ce_h / 2)],
               T["scs"], lx=(ce_x + ce_w + fl_x) / 2, ly=ce_y + ce_h / 2 - 8),
        # fleet -> Cloud Monitoring (Ops Agent push), bottom rail up into box bottom
        parrow([(fl_x + fl_w / 2, fl_y + fl_h), (fl_x + fl_w / 2, push_y),
                (mon_cx, push_y), (mon_cx, mon_y + mon_h + 4)],
               T["push"], lx=575, ly=push_y - 6),
    ]
    svg.append(text(W / 2, H - 16, T["cap"], 12, INK, "normal", "middle"))
    svg.append("</svg>")
    txt = "".join(svg)
    (OUT_DIR / f"runtime{suf}.svg").write_text(txt, encoding="utf-8")
    cairosvg.svg2png(bytestring=txt.encode("utf-8"), write_to=str(OUT_DIR / f"runtime{suf}.png"),
                     output_width=W * 2, output_height=H * 2)


def build():
    print("Fetching logos…")
    paths = {s: fetch(s) for s in ("git", "googlecloud", "docker")}
    build_one(paths, "en", "")
    build_one(paths, "kr", "_kr")
    print(f"Wrote runtime.png (EN) + runtime_kr.png to {OUT_DIR}")


if __name__ == "__main__":
    build()
