#!/usr/bin/env python3
"""Dark-only profile README + dashboard SVGs for Arnold-RG.

Designed for GitHub's dark theme (#0d1117). Called from collect_dashboard.py.
"""

from __future__ import annotations

import html
import re
from datetime import datetime
from pathlib import Path
from typing import Any

# Paired cards share one size so they sit side by side at 49% width.
CARD_W = 500
CARD_H = 272
BANNER_W = 900
BANNER_H = 210
FONT = "ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"

# GitHub dark
BG = "#0d1117"
CARD = "#161b22"
CARD2 = "#21262d"
TEXT = "#e6edf3"
MUTED = "#8b949e"
FAINT = "#6e7681"
BORDER = "#30363d"
ACCENT = "#58a6ff"
ACCENT_DIM = "#1f6feb"
SUCCESS = "#3fb950"
SUCCESS_BG = "#12261a"
ACCENT_BG = "#0d2137"
WARNING = "#d29922"
WARNING_BG = "#2d2106"
DANGER = "#f85149"
GRID = "#21262d"

SKILLICONS = "https://skillicons.dev/icons"

# Evidence-based stacks from public repo manifests (package.json, requirements,
# pubspec, Dockerfiles, Terraform). Icons omitted when not actually used.
STACK_ICONS: dict[str, list[str]] = {
    "2daymovie": ["py", "flask", "docker", "postgres"],
    "AbroadCost": ["js", "html", "css"],
    "ai-data-scientist-roadmap": ["py", "sklearn"],
    "arnold-portfolio": ["html", "css", "js"],
    "Arnold-RG": ["html", "css", "js"],
    "Arnold-RG.github.io": ["ts", "react", "vite"],
    "Boutique-la-difference": ["js", "html", "css"],
    "kingdom-life-krakow": ["html", "css", "js"],
    "nfl-bot": ["dart", "flutter", "py", "fastapi"],
    "our-money-hub": ["js", "react", "vite"],
    "peakwise": ["py", "fastapi", "react", "ts"],
    "ragi": ["ts", "prisma", "vite", "docker"],
    "STANS": ["ts", "react", "vite", "docker"],
    "vira": ["html", "css", "js"],
    "Vira-HQ": ["html", "css"],
    "worldshield-soc": ["py", "js", "html"],
}

DISPLAY_NAME: dict[str, str] = {
    "2daymovie": "2daymovie",
    "AbroadCost": "AbroadCost",
    "ai-data-scientist-roadmap": "AI & Data Roadmap",
    "arnold-portfolio": "Portfolio",
    "Arnold-RG": "Profile site",
    "Arnold-RG.github.io": "Root + Hamwe",
    "Boutique-la-difference": "Boutique La Différence",
    "kingdom-life-krakow": "Kingdom Life Kraków",
    "nfl-bot": "Elvora",
    "our-money-hub": "Our Money Hub",
    "peakwise": "Peakwise",
    "ragi": "RAGI",
    "STANS": "STANS",
    "vira": "Vira",
    "Vira-HQ": "Vira HQ",
    "worldshield-soc": "WorldShield SOC",
}

# Profile-wide rows (only tools found in public repos).
STACK_ROWS: list[tuple[str, list[str]]] = [
    ("Languages", ["ts", "dart", "py", "js", "html", "css", "bash"]),
    ("Frameworks", ["react", "flutter", "fastapi", "flask", "vite", "tailwind", "prisma", "threejs"]),
    ("Tools & Cloud", ["nodejs", "git", "github", "githubactions", "docker", "linux", "postgres", "terraform"]),
]

ICON_LABELS = {
    "ts": "TypeScript",
    "dart": "Dart",
    "py": "Python",
    "js": "JavaScript",
    "html": "HTML",
    "css": "CSS",
    "bash": "Bash",
    "react": "React",
    "flutter": "Flutter",
    "fastapi": "FastAPI",
    "flask": "Flask",
    "vite": "Vite",
    "tailwind": "Tailwind CSS",
    "prisma": "Prisma",
    "threejs": "Three.js",
    "chartjs": "Chart.js",
    "nodejs": "Node.js",
    "git": "Git",
    "github": "GitHub",
    "githubactions": "GitHub Actions",
    "docker": "Docker",
    "linux": "Linux",
    "postgres": "PostgreSQL",
    "terraform": "Terraform",
    "jupyter": "Jupyter",
    "pandas": "pandas",
    "sklearn": "scikit-learn",
}


def esc(text: Any) -> str:
    return html.escape("" if text is None else str(text), quote=True)


def truncate(text: str, limit: int) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    cut = text[: max(0, limit - 1)].rstrip()
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut + "…"


def cache_tag(snap: dict[str, Any]) -> str:
    raw = snap.get("generated_at") or ""
    try:
        dt = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%Y%m%d%H%M")
    except ValueError:
        return re.sub(r"\D", "", raw)[:12] or "1"


def skills_url(icons: list[str]) -> str:
    return f"{SKILLICONS}?i={",".join(icons)}&theme=dark&perline={len(icons)}"


def skills_alt(icons: list[str]) -> str:
    return ", ".join(ICON_LABELS.get(i, i) for i in icons)


# ---------------------------------------------------------------------------
# Header banner
# ---------------------------------------------------------------------------

def draw_header() -> str:
    w, h = BANNER_W, BANNER_H
    # Subtle tech grid + a few circuit traces. Name and subtitle centered.
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title desc">',
        '<title id="title">Arnold Rurangwa, Computer Engineer</title>',
        '<desc id="desc">Computer Engineer — Software, Cybersecurity, Applied AI.</desc>',
        "<defs>",
        f'<pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse">',
        f'<path d="M24 0H0V24" fill="none" stroke="#21262d" stroke-width="1"/>',
        "</pattern>",
        '<linearGradient id="fade" x1="0" y1="0" x2="0" y2="1">',
        f'<stop offset="0%" stop-color="{BG}" stop-opacity="0.15"/>',
        f'<stop offset="40%" stop-color="{BG}" stop-opacity="0.55"/>',
        f'<stop offset="100%" stop-color="{BG}" stop-opacity="0.92"/>',
        "</linearGradient>",
        '<style>',
        f"text{{font-family:{FONT}; fill:{TEXT};}}",
        ".caret{animation:blink 1.1s step-end infinite;}",
        "@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}",
        ".t1{animation:cycle 9s infinite;}",
        ".t2{animation:cycle 9s infinite 4.5s; opacity:0;}",
        "@keyframes cycle{0%{opacity:0}8%{opacity:1}42%{opacity:1}50%{opacity:0}100%{opacity:0}}",
        "</style>",
        "</defs>",
        f'<rect width="{w}" height="{h}" rx="12" fill="{BG}"/>',
        f'<rect width="{w}" height="{h}" rx="12" fill="url(#grid)"/>',
        f'<rect width="{w}" height="{h}" rx="12" fill="url(#fade)"/>',
        # Circuit traces (corners)
        f'<g fill="none" stroke="{ACCENT_DIM}" stroke-width="1.2" stroke-linecap="round" opacity="0.55">',
        '<path d="M28 28h90v0 M28 28v54 M118 28v18h22"/>',
        f'<path d="M{w-28} 28h-90 M{w-28} 28v54 M{w-118} 28v18h-22"/>',
        f'<path d="M28 {h-28}h70v0 M28 {h-28}v-40 M98 {h-28}v-14h18"/>',
        f'<path d="M{w-28} {h-28}h-70 M{w-28} {h-28}v-40"/>',
        "</g>",
        f'<g fill="{ACCENT}" opacity="0.7">',
        '<circle cx="28" cy="28" r="2.4"/>',
        '<circle cx="118" cy="46" r="2"/>',
        f'<circle cx="{w-28}" cy="28" r="2.4"/>',
        f'<circle cx="{w-118}" cy="46" r="2"/>',
        f'<circle cx="28" cy="{h-28}" r="2.4"/>',
        f'<circle cx="{w-28}" cy="{h-28}" r="2.4"/>',
        "</g>",
        # Accent rule under the name
        f'<rect x="{(w-180)/2:.1f}" y="92" width="180" height="2" rx="1" fill="{ACCENT}"/>',
        f'<text x="{w/2}" y="78" text-anchor="middle" font-size="42" font-weight="700" letter-spacing="-0.8">Arnold Rurangwa</text>',
        f'<text x="{w/2}" y="118" text-anchor="middle" font-size="15" fill="{MUTED}" letter-spacing="0.4">Computer Engineer · Software · Cybersecurity · Applied AI</text>',
        # Typing / cycling line
        f'<text class="t1" x="{w/2}" y="172" text-anchor="middle" font-size="14" fill="{ACCENT}">Building practical systems <tspan class="caret">|</tspan></text>',
        f'<text class="t2" x="{w/2}" y="172" text-anchor="middle" font-size="14" fill="{ACCENT}">Open to engineering roles <tspan class="caret">|</tspan></text>',
        f'<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="12" fill="none" stroke="{BORDER}"/>',
        "</svg>\n",
    ]
    return "\n".join(lines)


def card_open(title: str, desc: str, right: str = "") -> str:
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_W}" height="{CARD_H}" viewBox="0 0 {CARD_W} {CARD_H}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{esc(title)}</title>',
        f'<desc id="desc">{esc(desc)}</desc>',
        f"<style>text{{font-family:{FONT}; fill:{TEXT};}} .muted{{fill:{MUTED};}} .faint{{fill:{FAINT};}} .title{{font-weight:600; font-size:14px; fill:{TEXT};}}</style>",
        f'<rect width="{CARD_W}" height="{CARD_H}" rx="12" fill="{CARD}" stroke="{BORDER}"/>',
        f'<text x="20" y="28" class="title">{esc(title)}</text>',
    ]
    if right:
        svg.append(
            f'<text x="{CARD_W-20}" y="28" class="muted" text-anchor="end" font-size="11">{esc(right)}</text>'
        )
    return "\n".join(svg)


def card_close() -> str:
    return "</svg>\n"


def draw_kpis(snap: dict[str, Any]) -> str:
    k = snap["kpis"]
    items = [
        (str(k["repos"]), "Repositories"),
        (f"{k['commits_365']:,}", "Commits / 12 mo"),
        (str(k["live_pages"]), "Live sites"),
        (str(k["languages"]), "Languages"),
        (str(k["open_prs"]), "Open PRs"),
        (str(k["open_issues"]), "Open issues"),
        (str(k["stars"]), "Stars"),
        (str(snap["status_counts"].get("Live · in development", 0)), "In development"),
    ]
    parts = [card_open("Snapshot", "Key public GitHub figures.", snap["generated_at_display"])]
    cols, rows = 4, 2
    gap, left, top = 10, 16, 44
    cell_w = (CARD_W - left * 2 - gap * (cols - 1)) / cols
    cell_h = (CARD_H - top - 16 - gap) / rows
    for i, (value, label) in enumerate(items):
        r, c = divmod(i, cols)
        x = left + c * (cell_w + gap)
        y = top + r * (cell_h + gap)
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell_w:.1f}" height="{cell_h:.1f}" rx="8" fill="{BG}" stroke="{BORDER}"/>'
        )
        parts.append(
            f'<text x="{x+cell_w/2:.1f}" y="{y+34:.1f}" text-anchor="middle" font-size="22" font-weight="700">{esc(value)}</text>'
        )
        parts.append(
            f'<text x="{x+cell_w/2:.1f}" y="{y+52:.1f}" text-anchor="middle" class="muted" font-size="11">{esc(label)}</text>'
        )
    parts.append(card_close())
    return "".join(parts)


def draw_status(snap: dict[str, Any]) -> str:
    counts = snap["status_counts"]
    order = [
        ("Live", SUCCESS, SUCCESS_BG),
        ("Live · in development", ACCENT, ACCENT_BG),
        ("In progress", WARNING, WARNING_BG),
        ("Dormant", MUTED, CARD2),
    ]
    total = max(sum(counts.values()), 1)
    parts = [card_open("Status", "Live, in development, in progress, and dormant repositories.", f"{total} public repos")]
    x, y, w, h = 20, 48, CARD_W - 40, 16
    parts.append(f'<defs><clipPath id="bar"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8"/></clipPath></defs>')
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{CARD2}"/>')
    cursor = x
    segs = [(label, color, bg, counts.get(label, 0)) for label, color, bg in order if counts.get(label, 0)]
    for i, (label, color, _bg, n) in enumerate(segs):
        sw = w * (n / total)
        if i == len(segs) - 1:
            sw = x + w - cursor
        parts.append(
            f'<rect x="{cursor:.1f}" y="{y}" width="{sw:.1f}" height="{h}" fill="{color}" clip-path="url(#bar)"/>'
        )
        cursor += sw

    # 2x2 tiles so four statuses fit the same card size.
    gap = 8
    tile_w = (CARD_W - 40 - gap) / 2
    tile_h = 86
    for i, (label, color, bg) in enumerate(order):
        row, col = divmod(i, 2)
        tx = 20 + col * (tile_w + gap)
        ty = 76 + row * (tile_h + gap)
        n = counts.get(label, 0)
        parts.append(
            f'<rect x="{tx:.1f}" y="{ty}" width="{tile_w:.1f}" height="{tile_h}" rx="8" fill="{bg}" stroke="{BORDER}"/>'
        )
        parts.append(f'<circle cx="{tx+16:.1f}" cy="{ty+20}" r="4.5" fill="{color}"/>')
        parts.append(
            f'<text x="{tx+26:.1f}" y="{ty+24}" font-size="12" font-weight="600">{esc(label)}</text>'
        )
        parts.append(
            f'<text x="{tx+16:.1f}" y="{ty+66}" font-size="32" font-weight="700">{n}</text>'
        )
    parts.append(card_close())
    return "".join(parts)


def draw_activity(snap: dict[str, Any]) -> str:
    weekly = snap.get("weekly") or []
    weekly_sum = sum(w.get("total") or 0 for w in weekly)
    parts = [
        card_open(
            "Commits · 12 months",
            "Weekly commits across public repositories.",
            f"{weekly_sum:,} in 52 weeks",
        )
    ]
    plot_x, plot_y = 40, 48
    plot_w, plot_h = CARD_W - 56, 180
    max_v = max((w.get("total") or 0 for w in weekly), default=0) or 1
    for frac in (0, 0.5, 1):
        y = plot_y + plot_h - plot_h * frac
        parts.append(
            f'<line x1="{plot_x}" y1="{y:.1f}" x2="{plot_x+plot_w}" y2="{y:.1f}" stroke="{GRID}" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{plot_x-6}" y="{y+4:.1f}" class="faint" font-size="10" text-anchor="end">{int(round(max_v * frac))}</text>'
        )
    n = max(len(weekly), 1)
    gap = 1.6
    bar_w = max(2.2, (plot_w - gap * (n - 1)) / n)
    for i, week in enumerate(weekly):
        x = plot_x + i * (bar_w + gap)
        total = week.get("total") or 0
        h = 0 if max_v == 0 else (total / max_v) * (plot_h - 2)
        y = plot_y + plot_h - h
        parts.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_w:.2f}" height="{h:.2f}" rx="1" fill="{ACCENT}">'
            f'<title>{esc(week.get("date") or "")}: {total} commits</title></rect>'
        )
        if week.get("label"):
            parts.append(
                f'<text x="{x + bar_w/2:.2f}" y="{plot_y+plot_h+16:.1f}" class="faint" font-size="10" text-anchor="middle">{esc(week["label"])}</text>'
            )
    parts.append(card_close())
    return "".join(parts)


def draw_languages(snap: dict[str, Any]) -> str:
    langs = list(snap.get("languages") or [])
    top = langs[:6]
    other = langs[6:]
    if other:
        top.append(
            {
                "name": "Other",
                "bytes": sum(x.get("bytes") or 0 for x in other),
                "pct": sum(x.get("pct") or 0 for x in other),
                "color": FAINT,
            }
        )
    parts = [
        card_open(
            "Languages",
            "Language breakdown by bytes across public repositories.",
            f"{snap['kpis']['repos']} repos",
        )
    ]
    bar_x, bar_w = 120, CARD_W - 120 - 70
    row_h = 28
    start_y = 50
    # Vertically center the rows in the remaining space.
    block_h = row_h * max(len(top), 1)
    avail = CARD_H - start_y - 16
    if block_h < avail:
        start_y += int((avail - block_h) / 2) - 4
    for i, lang in enumerate(top):
        y = start_y + i * row_h
        parts.append(f'<text x="20" y="{y+13}" font-size="12">{esc(lang["name"])}</text>')
        parts.append(
            f'<rect x="{bar_x}" y="{y}" width="{bar_w}" height="16" rx="4" fill="{BG}"/>'
        )
        w = max(2, bar_w * ((lang.get("pct") or 0) / 100.0))
        color = lang.get("color") or ACCENT
        parts.append(
            f'<rect x="{bar_x}" y="{y}" width="{w:.1f}" height="16" rx="4" fill="{esc(color)}"/>'
        )
        parts.append(
            f'<text x="{bar_x+bar_w+8}" y="{y+13}" class="muted" font-size="11">{lang.get("pct", 0):.1f}%</text>'
        )
    parts.append(card_close())
    return "".join(parts)


STATUS_BADGE_SLUGS = {
    "Live": "live",
    "Live · in development": "live-in-dev",
    "In progress": "in-progress",
    "Dormant": "dormant",
}


def draw_badges() -> dict[str, str]:
    specs = {
        "live": ("Live", SUCCESS, SUCCESS_BG, SUCCESS),
        "live-in-dev": ("Live · in development", ACCENT, ACCENT_BG, ACCENT),
        "in-progress": ("In progress", WARNING, WARNING_BG, WARNING),
        "dormant": ("Dormant", MUTED, CARD2, BORDER),
    }
    out: dict[str, str] = {}
    for slug, (label, fg, bg, border) in specs.items():
        w = 10 + int(len(label) * 6.6) + 10
        h = 20
        out[slug] = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}">'
            f"<title>{esc(label)}</title>"
            f'<rect width="{w}" height="{h}" rx="10" fill="{bg}" stroke="{border}"/>'
            f'<text x="{w/2:.1f}" y="14.5" text-anchor="middle" font-family="{FONT}" font-size="11" font-weight="600" fill="{fg}">{esc(label)}</text>'
            f"</svg>\n"
        )
    return out


def status_badge_img(status: str, cache: str) -> str:
    slug = STATUS_BADGE_SLUGS[status]
    return f'<img src="dashboard/badge-{slug}.svg?v={cache}" alt="{esc(status)}" height="20">'


def stack_img(icons: list[str], height: int = 22) -> str:
    if not icons:
        return "—"
    return (
        f'<img src="{esc(skills_url(icons))}" alt="{esc(skills_alt(icons))}" height="{height}" style="height:{height}px;width:auto;">'
    )


# ---------------------------------------------------------------------------
# README
# ---------------------------------------------------------------------------


SAFE_DESC = {
    # The public GitHub description includes a venue address; keep the profile copy address-free.
    "kingdom-life-krakow": "Public English-language church website.",
}


def one_line_desc(repo: dict[str, Any]) -> str:
    if repo.get("name") in SAFE_DESC:
        return SAFE_DESC[repo["name"]]
    desc = repo.get("description") or "—"
    prefixes = [repo.get("name") or "", DISPLAY_NAME.get(repo.get("name") or "", "")]
    for prefix in prefixes:
        if prefix and desc.lower().startswith(prefix.lower()):
            desc = re.sub(r"^" + re.escape(prefix) + r"\s*[—–\-:]*\s*", "", desc, flags=re.I)
            break
    desc = truncate(desc, 88)
    if desc and desc[0].islower():
        desc = desc[0].upper() + desc[1:]
    return desc


def build_readme(snap: dict[str, Any]) -> str:
    cache = cache_tag(snap)
    k = snap["kpis"]
    ip = snap.get("in_progress") or {}
    human = ip.get("human_prs") or []
    issues = ip.get("issues") or []
    branches = ip.get("branches_ahead") or []
    dep_n = ip.get("dependabot_pr_count")
    if dep_n is None:
        dep_n = len(ip.get("dependabot_prs") or [])
    dep_by = ip.get("dependabot_by_repo") or {}
    if not dep_by and ip.get("dependabot_prs"):
        for pr in ip["dependabot_prs"]:
            dep_by[pr["repo"]] = dep_by.get(pr["repo"], 0) + 1
    failing = ip.get("failing_ci") or []
    events = snap.get("events") or []

    issue_word = "issue" if k["open_issues"] == 1 else "issues"
    pr_word = "pull request" if k["open_prs_human"] == 1 else "pull requests"

    # --- header, about, stack ---
    stack_blocks = []
    for title, icons in STACK_ROWS:
        stack_blocks.append(
            f"<p><strong>{esc(title)}</strong></p>\n"
            f'<p><img src="{esc(skills_url(icons))}" alt="{esc(skills_alt(icons))}"></p>'
        )
    stack_html = "\n".join(stack_blocks)

    lines: list[str] = [
        '<div align="center">',
        f'<img src="assets/header.svg?v={cache}" alt="Arnold Rurangwa, Computer Engineer" width="{BANNER_W}" height="{BANNER_H}">',
        "",
        "<p>",
        '<a href="https://arnold-rg.github.io/arnold-portfolio/">Portfolio</a>',
        "&nbsp;·&nbsp;",
        '<a href="https://arnold-rg.github.io/Arnold-RG/">Profile</a>',
        "&nbsp;·&nbsp;",
        '<a href="https://www.linkedin.com/in/rurangwa-arnold-53b90520b/">LinkedIn</a>',
        "&nbsp;·&nbsp;",
        '<a href="mailto:rurangwaarnold32@gmail.com">Email</a>',
        "</p>",
        "</div>",
        "",
        "## About",
        "",
        "Computer engineer working in software, Linux and IT support, and cybersecurity / SOC. "
        "I design understandable systems, careful interfaces, and explicit security boundaries.",
        "",
        "## Stack",
        "",
        '<div align="center">',
        "",
        stack_html,
        "",
        "<p><strong>Security</strong></p>",
        "<p>SOC dashboards · secure application design · public threat-intel feeds</p>",
        "",
        "</div>",
        "",
        "## Work",
        "",
        '<p align="center">',
        f'<img src="dashboard/kpis.svg?v={cache}" alt="Snapshot of public repositories, commits, live sites, pull requests and issues" width="49%">',
        f'<img src="dashboard/status.svg?v={cache}" alt="Repositories by status: live, live in development, in progress, or dormant" width="49%">',
        "</p>",
        '<p align="center">',
        f'<img src="dashboard/activity.svg?v={cache}" alt="Weekly commit activity across public repositories, last 12 months" width="49%">',
        f'<img src="dashboard/languages.svg?v={cache}" alt="Language breakdown across public repositories" width="49%">',
        "</p>",
        "",
        f'<p align="center"><sub>Data as of {esc(snap["generated_at_display"])} Europe/Warsaw · '
        f'{k["repos"]} public repositories · {k["commits_365"]:,} commits in 12 months · '
        f'{k["live_pages"]} live sites · {k["open_prs_human"]} {pr_word} in hand, {dep_n} Dependabot · '
        f'{k["open_issues"]} open {issue_word}. Refreshed every six hours.</sub></p>',
        "",
        "<sub>Live: Pages returned HTTP 200, with no open in-hand pull requests or ahead branches. "
        "Live · in development: the site is live, and there are open in-hand or draft pull requests, or a branch ahead of default. "
        "In progress: no live site yet. Dormant: no push in 90 days. Dependabot pull requests do not change the status.</sub>",
        "",
        "### Projects",
        "",
        "<table>",
        "<thead>",
        "<tr>",
        '<th align="left">Project</th>',
        '<th align="left">Description</th>',
        '<th align="left">Stack</th>',
        '<th align="left">Status</th>',
        '<th align="left">Live</th>',
        "</tr>",
        "</thead>",
        "<tbody>",
    ]

    repos = sorted(snap["repos"], key=lambda r: DISPLAY_NAME.get(r["name"], r["name"]).lower())
    for repo in repos:
        name = repo["name"]
        label = DISPLAY_NAME.get(name, name)
        desc = one_line_desc(repo)
        icons = STACK_ICONS.get(name) or []
        live = repo.get("live_label") or "—"
        pages = repo.get("pages_url")
        if pages and live == "Live":
            live_html = f'<a href="{esc(pages)}">Live</a>'
        elif pages and live not in {"No Pages"}:
            live_html = f'<a href="{esc(pages)}">{esc(live)}</a>'
        else:
            live_html = esc(live)
        lines += [
            "<tr>",
            f'<td><a href="{esc(repo["url"])}">{esc(label)}</a></td>',
            f"<td>{esc(desc)}</td>",
            f"<td>{stack_img(icons)}</td>",
            f"<td>{status_badge_img(repo['status'], cache)}</td>",
            f"<td>{live_html}</td>",
            "</tr>",
        ]
    lines += ["</tbody>", "</table>", ""]

    # Open work, collapsed
    summary = f"Open work — {len(human)} {pr_word}, {len(issues)} {issue_word}, {len(branches)} branches ahead"
    lines += ["<details>", f"<summary>{esc(summary)}</summary>", ""]
    lines.append(f"Dependabot: {dep_n} open pull requests" + (f" across {len(dep_by)} repositories." if dep_by else "."))
    lines.append("")
    if human:
        lines.append("**Pull requests**")
        lines.append("")
        for pr in sorted(human, key=lambda p: (p["repo"], p["number"])):
            flag = "draft · " if pr.get("isDraft") else ""
            title = truncate(pr.get("title") or "", 90)
            url = pr.get("url") or f"https://github.com/Arnold-RG/{pr['repo']}/pull/{pr['number']}"
            lines.append(f"- [{pr['repo']}#{pr['number']}]({url}) — {flag}{title}")
        lines.append("")
    if issues:
        lines.append("**Issues**")
        lines.append("")
        for iss in issues:
            url = iss.get("url") or f"https://github.com/Arnold-RG/{iss['repo']}/issues/{iss['number']}"
            lines.append(f"- [{iss['repo']}#{iss['number']}]({url}) — {truncate(iss.get('title') or '', 90)}")
        lines.append("")
    if branches:
        lines.append("**Branches ahead of default**")
        lines.append("")
        for b in branches:
            ahead = b.get("ahead") or 0
            behind = b.get("behind") or 0
            extra = f", {behind} behind" if behind else ""
            url = b.get("url") or f"https://github.com/Arnold-RG/{b['repo']}/tree/{b['name']}"
            lines.append(f"- [{b['repo']}/{b['name']}]({url}) — {ahead} ahead{extra}")
        lines.append("")
    if failing:
        lines.append("**Failing latest workflows**")
        lines.append("")
        for f in failing:
            label = f"{f['repo']} · {f.get('name') or 'workflow'} ({f.get('conclusion')})"
            if f.get("url"):
                lines.append(f"- [{label}]({f['url']})")
            else:
                lines.append(f"- {label}")
        lines.append("")
    else:
        lines.append("Latest workflows are passing on every public repository.")
        lines.append("")
    lines += ["</details>", ""]

    lines += ["<details>", "<summary>Recent activity</summary>", ""]
    if events:
        for ev in events:
            lines.append(f"- {event_md(ev)}")
    else:
        lines.append("No recent public push or pull-request events.")
    lines += ["", "</details>", ""]

    lines += [
        "## Education",
        "",
        "**B.Sc. Computer Engineering — Cybersecurity** · Wrocławska Akademia Biznesu WSH · 2022–2025",
        "",
        "## Security",
        "",
        "Vulnerability reports for any Arnold-RG project: see each repository’s `SECURITY.md`, or email **rurangwaarnold32@gmail.com**. Prefer private disclosure for unpatched findings.",
        "",
    ]
    return "\n".join(lines)


def event_md(ev: dict[str, Any]) -> str:
    when = ev.get("createdAt") or ""
    try:
        from datetime import datetime, timezone
        from zoneinfo import ZoneInfo
        dt = datetime.fromisoformat(when.replace("Z", "+00:00")).astimezone(ZoneInfo("Europe/Warsaw"))
        when = dt.strftime(f"{dt.day} %b %Y, %H:%M")
    except Exception:
        pass
    repo = ev.get("repo") or ""
    if ev.get("type") == "push":
        branch = ev.get("branch") or "default"
        head = (ev.get("head") or "")[:7]
        detail = ev["messages"][0] if ev.get("messages") else (head or "")
        line = f"{when}  {repo}  pushed to {branch}"
        if detail:
            line += f" — {detail}"
        return line
    action = ev.get("action") or "updated"
    draft = "draft " if ev.get("draft") else ""
    title = ev.get("title") or ""
    line = f"{when}  {repo}  {action} {draft}PR #{ev.get('number')}"
    if title:
        line += f" — {title}"
    return line


def write_site(root: Path, snap: dict[str, Any]) -> None:
    dash = root / "dashboard"
    assets = root / "assets"
    dash.mkdir(parents=True, exist_ok=True)
    assets.mkdir(parents=True, exist_ok=True)

    (assets / "header.svg").write_text(draw_header(), encoding="utf-8")
    (dash / "kpis.svg").write_text(draw_kpis(snap), encoding="utf-8")
    (dash / "status.svg").write_text(draw_status(snap), encoding="utf-8")
    (dash / "activity.svg").write_text(draw_activity(snap), encoding="utf-8")
    (dash / "languages.svg").write_text(draw_languages(snap), encoding="utf-8")
    for slug, svg in draw_badges().items():
        (dash / f"badge-{slug}.svg").write_text(svg, encoding="utf-8")

    # Remove the previous light/dark pairs and the long-list SVGs.
    stale = [
        "kpis-light.svg",
        "kpis-dark.svg",
        "status-light.svg",
        "status-dark.svg",
        "activity-light.svg",
        "activity-dark.svg",
        "languages-light.svg",
        "languages-dark.svg",
        "in-progress-light.svg",
        "in-progress-dark.svg",
        "recent-light.svg",
        "recent-dark.svg",
        "badge-shipped.svg",
    ]
    for name in stale:
        path = dash / name
        if path.exists():
            path.unlink()

    (root / "README.md").write_text(build_readme(snap), encoding="utf-8")
