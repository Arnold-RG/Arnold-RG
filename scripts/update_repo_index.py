#!/usr/bin/env python3
"""Regenerate the 'All public repositories' table in README.md and the
repository count in assets/stats.svg from the live GitHub API.

The table lives between <!-- REPO-INDEX:START --> and <!-- REPO-INDEX:END -->.
Private repositories and forks are never listed. Run by
.github/workflows/update-repo-index.yml; safe to run locally too.
"""
import json, os, re, urllib.request
from datetime import datetime, timezone
from pathlib import Path

USER = "Arnold-RG"
ROOT = Path(__file__).resolve().parent.parent
START, END = "<!-- REPO-INDEX:START -->", "<!-- REPO-INDEX:END -->"


def fetch_repos():
    """Return all public, non-fork repositories of USER, sorted A to Z."""
    headers = {"Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    repos, page = [], 1
    while True:
        url = f"https://api.github.com/users/{USER}/repos?type=owner&per_page=100&page={page}"
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as resp:
            batch = json.load(resp)
        if not batch:
            break
        repos += [r for r in batch if not r["private"] and not r["fork"]]
        page += 1
    return sorted(repos, key=lambda r: r["name"].lower())


def cell(text):
    return (text or "").replace("|", "/").replace("\n", " ").replace("<", "&lt;").strip()


COLORS = {"Python": "3776AB", "TypeScript": "3178C6", "JavaScript": "F7DF1E", "HTML": "E34F26",
          "CSS": "663399", "Dart": "0175C2", "Shell": "4EAA25", "PowerShell": "5391FE",
          "Kotlin": "7F52FF", "Swift": "F05138", "Dockerfile": "2496ED", "SCSS": "CC6699"}


def get_json(url):
    headers = {"Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as resp:
        return json.load(resp)


def badge(label, color):
    from urllib.parse import quote
    safe = quote(label.replace("-", "--").replace("_", "__"))
    return f'<img src="https://img.shields.io/badge/{safe}-{color}?style=flat-square" alt="{cell(label)}">'


def card(r):
    """One project card: name, description, languages with share, and tools (repo topics)."""
    langs = get_json(r["languages_url"]) or {}
    total = sum(langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:5]
    lang_badges = " ".join(badge(f"{k} {v * 100 / total:.0f}%", COLORS.get(k, "6F4E37")) for k, v in top) or "-"
    topics = r.get("topics") or []
    tool_badges = " ".join(badge(t, "2b2d42") for t in topics[:8]) or "<sub>No topics set yet</sub>"
    links = f'<a href="{r["html_url"]}">Code</a>'
    if r.get("homepage"):
        links += f' · <a href="{r["homepage"]}">Live</a>'
    return (f'<td width="50%" valign="top">\n<h3><a href="{r["html_url"]}">{cell(r["name"])}</a></h3>\n'
            f'<p>{cell(r["description"])}</p>\n<p><b>Languages</b><br>{lang_badges}</p>\n'
            f'<p><b>Tools</b><br>{tool_badges}</p>\n<p>{links}</p>\n</td>')


def build_table(repos):
    lines = [START, "", f"Every public repository on this account ({len(repos)}), A to Z, with the languages "
             "(share of code, from GitHub) and tools (repository topics) each one uses. Updated automatically.",
             "", "<table>"]
    for i in range(0, len(repos), 2):
        lines.append("<tr>")
        lines += [card(r) for r in repos[i:i + 2]]
        lines.append("</tr>")
    return "\n".join(lines + ["</table>", "", END])


def main():
    repos = fetch_repos()
    n = len(repos)
    today = datetime.now(timezone.utc).strftime("%-d %B %Y")
    readme = ROOT / "README.md"
    text = readme.read_text()
    text = re.sub(re.escape(START) + r".*?" + re.escape(END), build_table(repos), text, flags=re.S)
    text = re.sub(r"\d+ public repositories, 0 stars \(count as of [^)]*\)",
                  f"{n} public repositories, 0 stars (count as of {today})", text)
    readme.write_text(text)
    svg = ROOT / "assets" / "stats.svg"
    s = svg.read_text()
    s = re.sub(r'(<text class="kpi" x="24" y="108">)\d+(</text>)', rf"\g<1>{n}\g<2>", s)
    s = re.sub(r"\d+ public repositories, 0 stars \(count as of [^)]*\)",
               f"{n} public repositories, 0 stars (count as of {today})", s)
    svg.write_text(s)
    print(f"{n} public repositories indexed")


if __name__ == "__main__":
    main()
