#!/usr/bin/env python3
"""Build overview/index.html: a dashboard of every public, non-fork repository
of Arnold-RG with its full file structure, languages (share of code), tools
(topics plus detected config files), file counts and links.

Data comes only from the GitHub REST API. Private repositories are never read.
Run by .github/workflows/update-repo-index.yml.
"""
import html, json, os, urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

USER = "Arnold-RG"
OUT = Path(__file__).resolve().parent.parent / "overview" / "index.html"

# Files whose presence tells us which tool or framework a repo uses.
DETECT = {
    "package.json": "Node.js", "requirements.txt": "pip", "pyproject.toml": "Python packaging",
    "Dockerfile": "Docker", "docker-compose.yml": "Docker Compose", "pubspec.yaml": "Flutter",
    "vite.config.ts": "Vite", "vite.config.js": "Vite", "tsconfig.json": "TypeScript",
    "render.yaml": "Render", "Procfile": "Procfile", "netlify.toml": "Netlify",
    "tailwind.config.js": "Tailwind CSS", "next.config.js": "Next.js", ".eslintrc.json": "ESLint",
    "eslint.config.js": "ESLint", "Makefile": "Make", "manifest.webmanifest": "PWA",
    "service-worker.js": "Service worker", "sw.js": "Service worker", "CNAME": "Custom domain",
}
COLORS = {"Python": "#3776AB", "TypeScript": "#3178C6", "JavaScript": "#F7DF1E", "HTML": "#E34F26",
          "CSS": "#663399", "Dart": "#0175C2", "Shell": "#4EAA25", "PowerShell": "#5391FE",
          "Dockerfile": "#2496ED", "SCSS": "#CC6699", "Kotlin": "#7F52FF", "Swift": "#F05138"}


def api(path):
    headers = {"Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    url = path if path.startswith("http") else f"https://api.github.com{path}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
        return json.load(r)


def repos():
    out, page = [], 1
    while True:
        batch = api(f"/users/{USER}/repos?type=owner&per_page=100&page={page}")
        if not batch:
            return sorted(out, key=lambda r: r["name"].lower())
        out += [r for r in batch if not r["private"] and not r["fork"]]
        page += 1


def tree_of(repo):
    """Recursive file list of the default branch (blobs and folders)."""
    t = api(f"/repos/{USER}/{repo['name']}/git/trees/{repo['default_branch']}?recursive=1")
    return t.get("tree", []), t.get("truncated", False)


def nest(entries):
    root = {}
    for e in entries:
        node = root
        parts = e["path"].split("/")
        for p in parts[:-1]:
            node = node.setdefault(p + "/", {})
        if e["type"] == "tree":
            node.setdefault(parts[-1] + "/", {})
        else:
            node[parts[-1]] = e.get("size", 0)
    return root


def render_tree(node, depth=0):
    items = sorted(node.items(), key=lambda kv: (not kv[0].endswith("/"), kv[0].lower()))
    rows = []
    for name, val in items:
        esc = html.escape(name)
        if isinstance(val, dict):
            n = count_files(val)
            inner = render_tree(val, depth + 1)
            rows.append(f'<li><details{" open" if depth == 0 and n < 15 else ""}><summary>'
                        f'<span class="dir">{esc}</span> <span class="muted">{n} files</span></summary>'
                        f'<ul>{inner}</ul></details></li>')
        else:
            rows.append(f'<li><span class="file">{esc}</span></li>')
    return "".join(rows)


def count_files(node):
    return sum(count_files(v) if isinstance(v, dict) else 1 for v in node.values())


def card(repo):
    langs = api(repo["languages_url"]) or {}
    total = sum(langs.values()) or 1
    entries, truncated = tree_of(repo)
    files = [e for e in entries if e["type"] == "blob"]
    names = {e["path"].split("/")[-1] for e in files}
    paths = {e["path"] for e in files}
    tools = list(dict.fromkeys(repo.get("topics") or []))
    detected = sorted({v for k, v in DETECT.items() if k in names})
    if any(p.startswith(".github/workflows/") for p in paths):
        detected.append("GitHub Actions")
    exts = Counter((p.rsplit(".", 1)[-1].lower() if "." in p.split("/")[-1] else "other") for p in paths)
    bar = "".join(f'<span style="width:{v * 100 / total:.2f}%;background:{COLORS.get(k, "#6F4E37")}" '
                  f'title="{html.escape(k)} {v * 100 / total:.1f}%"></span>' for k, v in
                  sorted(langs.items(), key=lambda kv: -kv[1]))
    legend = "".join(f'<li><i style="background:{COLORS.get(k, "#6F4E37")}"></i>{html.escape(k)} '
                     f'<b>{v * 100 / total:.1f}%</b></li>' for k, v in sorted(langs.items(), key=lambda kv: -kv[1]))
    chips = "".join(f'<span class="chip">{html.escape(t)}</span>' for t in tools)
    dchips = "".join(f'<span class="chip alt">{html.escape(t)}</span>' for t in detected)
    top_ext = ", ".join(f".{k} {v}" for k, v in exts.most_common(6))
    live = f' <a class="btn" href="{html.escape(repo["homepage"])}">Live site</a>' if repo.get("homepage") else ""
    updated = repo["pushed_at"][:10]
    note = '<p class="muted">Tree truncated by GitHub for size.</p>' if truncated else ""
    return f'''<article class="card" id="{html.escape(repo["name"])}" data-name="{html.escape(repo["name"].lower())}" data-lang="{html.escape(" ".join(langs).lower())}">
<header><h2>{html.escape(repo["name"])}</h2><span class="muted">updated {updated}</span></header>
<p>{html.escape(repo.get("description") or "")}</p>
<div class="stats"><div><b>{len(files)}</b><span>files</span></div><div><b>{len(langs)}</b><span>languages</span></div><div><b>{repo["size"]:,} KB</b><span>size</span></div><div><b>{html.escape(repo["default_branch"])}</b><span>branch</span></div></div>
<h3>Languages</h3><div class="bar">{bar}</div><ul class="legend">{legend or "<li>None detected</li>"}</ul>
<h3>Tools</h3><div class="chips">{chips}{dchips or ""}</div>
<p class="muted">File types: {html.escape(top_ext)}</p>
<details class="tree"><summary>Full structure ({len(files)} files)</summary><ul>{render_tree(nest(entries))}</ul>{note}</details>
<footer><a class="btn" href="{repo["html_url"]}">Code</a>{live}</footer>
</article>'''


def main():
    rs = repos()
    cards = [card(r) for r in rs]
    total_lang = Counter()
    for r in rs:
        for k, v in (api(r["languages_url"]) or {}).items():
            total_lang[k] += v
    tl = sum(total_lang.values()) or 1
    top = "".join(f'<li><i style="background:{COLORS.get(k, "#6F4E37")}"></i>{html.escape(k)} <b>{v * 100 / tl:.1f}%</b></li>'
                  for k, v in total_lang.most_common(8))
    now = datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Arnold Rurangwa · Every repository</title>
<link rel="stylesheet" href="overview.css"></head><body>
<header class="top"><div><p class="eyebrow">Arnold Rurangwa · GitHub</p><h1>Every repository, inside and out</h1>
<p class="muted">{len(rs)} public repositories with their full file structure, languages and tools. Generated from the GitHub API on {now}.</p></div>
<div class="kpis"><div><b>{len(rs)}</b><span>repos</span></div><div><b>{len(total_lang)}</b><span>languages</span></div></div></header>
<section class="overall"><h3>Languages across all repos</h3><ul class="legend">{top}</ul>
<input id="q" type="search" placeholder="Filter by name or language" aria-label="Filter repositories"></section>
<nav class="index">{"".join(f'<a href="#{html.escape(r["name"])}">{html.escape(r["name"])}</a>' for r in rs)}</nav>
<main class="grid">{"".join(cards)}</main>
<footer class="bottom"><a href="https://github.com/{USER}">github.com/{USER}</a></footer>
<script src="overview.js"></script></body></html>''')
    print(f"overview built: {len(rs)} repos")


if __name__ == "__main__":
    main()
