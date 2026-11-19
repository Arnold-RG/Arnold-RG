#!/usr/bin/env python3
"""Build the public work dashboard for the Arnold-RG profile README.

Public repositories only. Safe to run in GitHub Actions with GITHUB_TOKEN
(contents: write on this repository is enough to commit the result).

Usage (from the repository root):

    python3 scripts/collect_dashboard.py

The script writes dark-only SVGs under dashboard/, a public-safe data
snapshot at dashboard/data.json, and regenerates README.md and assets/header.svg.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

OWNER = "Arnold-RG"
TZ = ZoneInfo("Europe/Warsaw")
DORMANT_DAYS = 90
README_START = "<!-- profile-dashboard:start -->"
README_END = "<!-- profile-dashboard:end -->"
USER_AGENT = "Arnold-RG-profile-dashboard"
API_VERSION = "2022-11-28"

# Calendar width matches the existing profile banner.
SVG_WIDTH = 900
FONT = '-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif'

LIGHT = {
    "name": "light",
    "bg": "#ffffff",
    "card": "#f6f8fa",
    "card2": "#eef2f6",
    "text": "#1f2328",
    "muted": "#656d76",
    "faint": "#8c959f",
    "border": "#d0d7de",
    "accent": "#0969da",
    "accent_soft": "#ddf4ff",
    "success": "#1a7f37",
    "success_bg": "#dafbe1",
    "warning": "#9a6700",
    "warning_bg": "#fff8c5",
    "danger": "#d1242f",
    "danger_bg": "#ffebe9",
    "grid": "#d0d7de",
}

DARK = {
    "name": "dark",
    "bg": "#0d1117",
    "card": "#161b22",
    "card2": "#21262d",
    "text": "#e6edf3",
    "muted": "#8b949e",
    "faint": "#6e7681",
    "border": "#30363d",
    "accent": "#58a6ff",
    "accent_soft": "#13233a",
    "success": "#3fb950",
    "success_bg": "#12261a",
    "warning": "#d29922",
    "warning_bg": "#2d2106",
    "danger": "#f85149",
    "danger_bg": "#3d1214",
    "grid": "#30363d",
}

# GitHub language colours (fallback #8b949e).
LANG_COLORS = {
    "TypeScript": "#3178c6",
    "JavaScript": "#f1e05a",
    "Python": "#3572A5",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "Dart": "#00B4AB",
    "Java": "#b07219",
    "C++": "#f34b7d",
    "PHP": "#4F5D95",
    "Kotlin": "#A97BFF",
    "Dockerfile": "#384d54",
    "Shell": "#89e051",
    "SCSS": "#c6538c",
    "Go": "#00ADD8",
    "Rust": "#dea584",
    "C": "#555555",
    "Ruby": "#701516",
    "Swift": "#F05138",
    "Vue": "#41b883",
}


def repo_root() -> Path:
    here = Path(__file__).resolve()
    return here.parents[1]


def load_token() -> str:
    for key in ("GITHUB_TOKEN", "GH_TOKEN"):
        val = os.environ.get(key, "").strip()
        if val:
            return val
    try:
        out = subprocess.check_output(
            ["gh", "auth", "token"], text=True, stderr=subprocess.DEVNULL
        )
        token = out.strip()
        if token:
            return token
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    raise SystemExit(
        "No GitHub token found. Set GITHUB_TOKEN or GH_TOKEN, or run `gh auth login`."
    )


class GitHub:
    def __init__(self, token: str) -> None:
        self.token = token
        self._sema_delay = 0.0

    def _headers(self, accept: str = "application/vnd.github+json") -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": accept,
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": USER_AGENT,
        }

    def request(
        self,
        url: str,
        *,
        method: str = "GET",
        body: bytes | None = None,
        accept: str = "application/vnd.github+json",
        timeout: int = 45,
    ) -> tuple[int, dict[str, str], bytes]:
        req = urllib.request.Request(url, data=body, method=method, headers=self._headers(accept))
        for attempt in range(6):
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return resp.status, {k.lower(): v for k, v in resp.headers.items()}, resp.read()
            except urllib.error.HTTPError as exc:
                raw = exc.read() if exc.fp else b""
                if exc.code in {502, 503, 504, 429} or (
                    exc.code == 403 and b"rate limit" in raw.lower()
                ):
                    retry_after = exc.headers.get("Retry-After") if exc.headers else None
                    try:
                        wait = float(retry_after) if retry_after else 2.0 * (attempt + 1)
                    except ValueError:
                        wait = 2.0 * (attempt + 1)
                    time.sleep(min(wait, 20))
                    continue
                return exc.code, {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])}, raw
            except (urllib.error.URLError, TimeoutError):
                time.sleep(1.5 * (attempt + 1))
                continue
        return 0, {}, b""

    def json(self, path: str, params: dict[str, Any] | None = None) -> tuple[int, Any]:
        url = path if path.startswith("http") else f"https://api.github.com{path}"
        if params:
            url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
        status, _headers, raw = self.request(url)
        if not raw:
            return status, None
        try:
            return status, json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return status, None

    def graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
        status, _headers, raw = self.request(
            "https://api.github.com/graphql",
            method="POST",
            body=payload,
            accept="application/json",
        )
        if status != 200:
            raise SystemExit(f"GraphQL failed with HTTP {status}: {raw[:500]!r}")
        data = json.loads(raw.decode("utf-8"))
        if data.get("errors"):
            # Some field-level errors are tolerable; abort on complete failure.
            raise SystemExit(f"GraphQL errors: {data['errors']}")
        return data["data"]


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def fmt_warsaw(dt: datetime | None, with_time: bool = True) -> str:
    if not dt:
        return "—"
    local = dt.astimezone(TZ)
    if with_time:
        return local.strftime("%d %b %Y, %H:%M")
    return local.strftime("%d %b %Y")


def esc(text: Any) -> str:
    s = "" if text is None else str(text)
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def xml_escape_keep_newline(text: str) -> str:
    return esc(text)


def truncate(text: str, limit: int) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def is_bot_login(login: str | None) -> bool:
    if not login:
        return False
    lower = login.lower()
    return lower.endswith("[bot]") or lower in {"dependabot", "dependabot-preview", "github-actions"}


def is_dependabot(login: str | None, branch: str | None = None) -> bool:
    if login and "dependabot" in login.lower():
        return True
    if branch and branch.lower().startswith("dependabot/"):
        return True
    return False


GQL = """
query ($login: String!, $since30: GitTimestamp!, $since90: GitTimestamp!, $since365: GitTimestamp!) {
  user(login: $login) {
    repositories(
      first: 100
      privacy: PUBLIC
      ownerAffiliations: OWNER
      orderBy: { field: PUSHED_AT, direction: DESC }
    ) {
      nodes {
        name
        nameWithOwner
        description
        url
        homepageUrl
        isPrivate
        isFork
        isArchived
        stargazerCount
        forkCount
        createdAt
        updatedAt
        pushedAt
        primaryLanguage { name color }
        languages(first: 20, orderBy: { field: SIZE, direction: DESC }) {
          edges { size node { name color } }
        }
        issues(states: OPEN, first: 25) {
          totalCount
          nodes { number title url createdAt author { login } }
        }
        pullRequests(states: OPEN, first: 100) {
          totalCount
          nodes {
            number title url isDraft createdAt updatedAt
            author { login }
            headRefName
          }
        }
        defaultBranchRef {
          name
          target {
            ... on Commit {
              oid
              history30: history(since: $since30) { totalCount }
              history90: history(since: $since90) { totalCount }
              history365: history(since: $since365) { totalCount }
            }
          }
        }
        refs(refPrefix: "refs/heads/", first: 80) {
          totalCount
          nodes { name }
        }
      }
    }
  }
}
"""


def collect_repos(gh: GitHub, now: datetime) -> list[dict[str, Any]]:
    since30 = (now - timedelta(days=30)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    since90 = (now - timedelta(days=90)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    since365 = (now - timedelta(days=365)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    data = gh.graphql(
        GQL,
        {
            "login": OWNER,
            "since30": since30,
            "since90": since90,
            "since365": since365,
        },
    )
    nodes = data["user"]["repositories"]["nodes"]
    repos: list[dict[str, Any]] = []
    for node in nodes:
        if node.get("isPrivate"):
            # Defence in depth: never emit a private repository.
            continue
        default = (node.get("defaultBranchRef") or {}).get("name") or "main"
        target = ((node.get("defaultBranchRef") or {}).get("target")) or {}
        langs = []
        for edge in (node.get("languages") or {}).get("edges") or []:
            name = ((edge.get("node") or {}).get("name")) or "Other"
            langs.append(
                {
                    "name": name,
                    "bytes": int(edge.get("size") or 0),
                    "color": (edge.get("node") or {}).get("color") or LANG_COLORS.get(name, "#8b949e"),
                }
            )
        prs = []
        for pr in (node.get("pullRequests") or {}).get("nodes") or []:
            author = ((pr.get("author") or {}).get("login")) or "unknown"
            prs.append(
                {
                    "number": pr["number"],
                    "title": pr.get("title") or "",
                    "url": pr.get("url"),
                    "isDraft": bool(pr.get("isDraft")),
                    "createdAt": pr.get("createdAt"),
                    "updatedAt": pr.get("updatedAt"),
                    "author": author,
                    "headRefName": pr.get("headRefName") or "",
                    "dependabot": is_dependabot(author, pr.get("headRefName")),
                }
            )
        issues = []
        for issue in (node.get("issues") or {}).get("nodes") or []:
            issues.append(
                {
                    "number": issue["number"],
                    "title": issue.get("title") or "",
                    "url": issue.get("url"),
                    "createdAt": issue.get("createdAt"),
                    "author": ((issue.get("author") or {}).get("login")) or "unknown",
                }
            )
        branches = [b["name"] for b in ((node.get("refs") or {}).get("nodes") or []) if b.get("name")]
        primary = node.get("primaryLanguage") or {}
        repos.append(
            {
                "name": node["name"],
                "full_name": node["nameWithOwner"],
                "description": node.get("description") or "",
                "url": node["url"],
                "homepageUrl": node.get("homepageUrl") or "",
                "isFork": bool(node.get("isFork")),
                "isArchived": bool(node.get("isArchived")),
                "stars": int(node.get("stargazerCount") or 0),
                "forks": int(node.get("forkCount") or 0),
                "createdAt": node.get("createdAt"),
                "updatedAt": node.get("updatedAt"),
                "pushedAt": node.get("pushedAt"),
                "primaryLanguage": primary.get("name") or "—",
                "primaryLanguageColor": primary.get("color") or "#8b949e",
                "languages": langs,
                "issue_count": int((node.get("issues") or {}).get("totalCount") or 0),
                "issues": issues,
                "pr_count": int((node.get("pullRequests") or {}).get("totalCount") or 0),
                "prs": prs,
                "default_branch": default,
                "commits_30": int((target.get("history30") or {}).get("totalCount") or 0),
                "commits_90": int((target.get("history90") or {}).get("totalCount") or 0),
                "commits_365": int((target.get("history365") or {}).get("totalCount") or 0),
                "branch_names": branches,
                "branch_total": int((node.get("refs") or {}).get("totalCount") or len(branches)),
            }
        )
    return repos


def pages_url_for(repo: dict[str, Any]) -> str | None:
    home = (repo.get("homepageUrl") or "").strip()
    if "github.io" in home:
        return home if home.endswith("/") else home + "/"
    name = repo["name"]
    if name.lower() == f"{OWNER.lower()}.github.io":
        return f"https://{OWNER.lower()}.github.io/"
    # Conventional project Pages URL; confirmed later by the Pages API + HTTP check.
    return f"https://{OWNER.lower()}.github.io/{name}/"


def check_http(url: str, timeout: int = 15) -> int | None:
    req = urllib.request.Request(
        url,
        method="GET",
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return int(resp.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)
    except Exception:
        return None


def enrich_repo(gh: GitHub, repo: dict[str, Any]) -> dict[str, Any]:
    name = repo["name"]
    default = repo["default_branch"]

    # Pages metadata.
    pages_status, pages = gh.json(f"/repos/{OWNER}/{name}/pages")
    if pages_status == 200 and isinstance(pages, dict):
        html_url = pages.get("html_url") or pages_url_for(repo)
        repo["pages"] = {
            "enabled": True,
            "html_url": html_url,
            "status": pages.get("status"),
            "source": ((pages.get("source") or {}).get("branch")),
        }
    else:
        html_url = pages_url_for(repo)
        repo["pages"] = {"enabled": False, "html_url": html_url, "status": None, "source": None}

    repo["pages_url"] = repo["pages"]["html_url"]
    repo["pages_http"] = check_http(repo["pages_url"]) if repo["pages_url"] else None

    # Latest workflow run on the default branch.
    runs_status, runs = gh.json(
        f"/repos/{OWNER}/{name}/actions/runs",
        {"per_page": 1, "branch": default},
    )
    ci = None
    if runs_status == 200 and isinstance(runs, dict) and runs.get("workflow_runs"):
        run = runs["workflow_runs"][0]
        ci = {
            "name": run.get("name") or run.get("display_title") or "workflow",
            "status": run.get("status"),
            "conclusion": run.get("conclusion"),
            "url": run.get("html_url"),
            "event": run.get("event"),
            "branch": run.get("head_branch"),
            "createdAt": run.get("created_at"),
        }
    repo["ci"] = ci

    # Non-dependabot branches ahead of the default branch.
    ahead: list[dict[str, Any]] = []
    candidates = [
        b
        for b in repo.get("branch_names") or []
        if b != default and not b.lower().startswith("dependabot/")
    ]
    for branch in candidates:
        path = f"/repos/{OWNER}/{name}/compare/{urllib.parse.quote(default)}...{urllib.parse.quote(branch)}"
        st, cmp_ = gh.json(path)
        if st != 200 or not isinstance(cmp_, dict):
            continue
        ahead_by = int(cmp_.get("ahead_by") or 0)
        behind_by = int(cmp_.get("behind_by") or 0)
        if ahead_by > 0:
            ahead.append(
                {
                    "name": branch,
                    "ahead": ahead_by,
                    "behind": behind_by,
                    "url": f"https://github.com/{OWNER}/{name}/tree/{urllib.parse.quote(branch)}",
                }
            )
    repo["branches_ahead"] = ahead
    return repo


def sunday_utc(dt: datetime) -> datetime:
    utc = dt.astimezone(timezone.utc)
    sunday = utc - timedelta(days=(utc.weekday() + 1) % 7)
    return sunday.replace(hour=0, minute=0, second=0, microsecond=0)


def normalize_week_ts(ts: int) -> int:
    """Snap a week-start Unix timestamp to Sunday 00:00 UTC.

    Some GitHub stats payloads are one hour off around DST; shifting 12 hours
    first keeps those keys in the intended week instead of the previous one.
    """
    mid = datetime.fromtimestamp(ts, tz=timezone.utc) + timedelta(hours=12)
    return int(sunday_utc(mid).timestamp())


def collect_weekly_activity(gh: GitHub, repos: list[dict[str, Any]], now: datetime) -> list[dict[str, Any]]:
    # Align to 52 complete weeks ending this week (Sunday 00:00 UTC, as GitHub does).
    week_totals: dict[int, int] = {}
    for repo in repos:
        status, payload = gh.json(f"/repos/{OWNER}/{repo['name']}/stats/commit_activity")
        if status == 202:
            time.sleep(2)
            status, payload = gh.json(f"/repos/{OWNER}/{repo['name']}/stats/commit_activity")
        if status != 200 or not isinstance(payload, list):
            payload = commits_as_weekly(gh, repo["name"], now)
        for row in payload or []:
            week = int(row.get("week") or 0)
            if not week:
                continue
            key = normalize_week_ts(week)
            week_totals[key] = week_totals.get(key, 0) + int(row.get("total") or 0)

    end = int(sunday_utc(now).timestamp())
    series = []
    last_month = None
    for i in range(51, -1, -1):
        key = end - i * 7 * 86400
        dt = datetime.fromtimestamp(key, tz=timezone.utc).astimezone(TZ)
        month = dt.strftime("%b")
        label = month if month != last_month else ""
        last_month = month
        series.append(
            {
                "week": key,
                "total": week_totals.get(key, 0),
                "label": label,
                "date": dt.strftime("%Y-%m-%d"),
            }
        )
    return series


def commits_as_weekly(gh: GitHub, name: str, now: datetime) -> list[dict[str, Any]]:
    since = (now - timedelta(days=371)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    buckets: dict[int, int] = {}
    page = 1
    while page <= 10:
        status, payload = gh.json(
            f"/repos/{OWNER}/{name}/commits",
            {"since": since, "per_page": 100, "page": page},
        )
        if status != 200 or not isinstance(payload, list) or not payload:
            break
        for commit in payload:
            date_s = ((commit.get("commit") or {}).get("committer") or {}).get("date") or (
                (commit.get("commit") or {}).get("author") or {}
            ).get("date")
            dt = parse_iso(date_s)
            if not dt:
                continue
            # Sunday 00:00 UTC, matching GitHub's commit_activity buckets.
            utc = dt.astimezone(timezone.utc)
            key = int(sunday_utc(utc).timestamp())
            buckets[key] = buckets.get(key, 0) + 1
        if len(payload) < 100:
            break
        page += 1
    return [{"week": k, "total": v} for k, v in buckets.items()]


def collect_events(gh: GitHub, limit: int = 30) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for page in range(1, 4):
        status, payload = gh.json(f"/users/{OWNER}/events/public", {"per_page": 100, "page": page})
        if status != 200 or not isinstance(payload, list):
            break
        for ev in payload:
            etype = ev.get("type")
            repo_name = ((ev.get("repo") or {}).get("name") or "").split("/")[-1]
            created = ev.get("created_at")
            if etype == "PushEvent":
                payload = ev.get("payload") or {}
                ref = payload.get("ref") or ""
                branch = ref.replace("refs/heads/", "") if ref else ""
                commits = payload.get("commits") or []
                size = payload.get("size")
                if size is None:
                    size = payload.get("distinct_size")
                if size is None and commits:
                    size = len(commits)
                msgs = [(c.get("message") or "").split("\n", 1)[0] for c in commits[:3]]
                head = payload.get("head") or payload.get("after") or ""
                events.append(
                    {
                        "type": "push",
                        "repo": repo_name,
                        "createdAt": created,
                        "branch": branch,
                        "commits": size,
                        "messages": msgs,
                        "head": head,
                        "url": f"https://github.com/{OWNER}/{repo_name}",
                    }
                )
            elif etype == "PullRequestEvent":
                pr = (ev.get("payload") or {}).get("pull_request") or {}
                action = (ev.get("payload") or {}).get("action") or ""
                number = pr.get("number")
                events.append(
                    {
                        "type": "pr",
                        "repo": repo_name,
                        "createdAt": created,
                        "action": action,
                        "number": number,
                        "title": pr.get("title") or "",
                        "draft": pr.get("draft"),
                        "url": pr.get("html_url")
                        or pr.get("url")
                        or f"https://github.com/{OWNER}/{repo_name}/pull/{number}",
                        "author": ((pr.get("user") or {}).get("login")) or "",
                    }
                )
            if len(events) >= limit:
                return events
        if len(payload) < 100:
            break
    return events[:limit]


def _in_hand_work(repo: dict[str, Any]) -> bool:
    """Open in-hand (non-Dependabot) PRs, including drafts, or a branch ahead of default."""
    prs = repo.get("prs")
    if prs is not None:
        if any(not p.get("dependabot") for p in prs):
            return True
    elif int(repo.get("human_pr_count") or 0) > 0:
        return True
    return bool(repo.get("branches_ahead"))


def classify(repo: dict[str, Any], now: datetime) -> str:
    """Live / Live · in development / In progress / Dormant.

    Recent pushes alone do not make a repository 'In progress'. Dependabot
    pull requests do not count as in-hand work. A repository with no push in
    90 days is Dormant, even if a Pages site is still up.
    """
    pushed = parse_iso(repo.get("pushedAt"))
    stale = pushed is None or (now - pushed) > timedelta(days=DORMANT_DAYS)
    if stale:
        return "Dormant"
    live = repo.get("pages_http") == 200
    if live and not _in_hand_work(repo):
        return "Live"
    if live:
        return "Live · in development"
    return "In progress"


def ci_label(ci: dict[str, Any] | None) -> str:
    if not ci:
        return "No runs"
    status = ci.get("status")
    conclusion = ci.get("conclusion")
    if status in {"queued", "in_progress", "pending", "waiting"}:
        return "Running"
    if conclusion == "success":
        return "Passing"
    if conclusion in {"failure", "timed_out", "startup_failure"}:
        return "Failing"
    if conclusion == "cancelled":
        return "Cancelled"
    if conclusion == "skipped":
        return "Skipped"
    if conclusion == "action_required":
        return "Action required"
    return (conclusion or status or "Unknown").replace("_", " ").title()


def live_label(repo: dict[str, Any]) -> str:
    code = repo.get("pages_http")
    if code == 200:
        return "Live"
    if code is None and not repo.get("pages", {}).get("enabled"):
        return "No Pages"
    if code is None:
        return "Unreachable"
    return f"HTTP {code}"


def build_snapshot(repos: list[dict[str, Any]], weekly: list[dict[str, Any]], events: list[dict[str, Any]], now: datetime) -> dict[str, Any]:
    for repo in repos:
        repo["status"] = classify(repo, now)
        repo["ci_label"] = ci_label(repo.get("ci"))
        repo["live_label"] = live_label(repo)
        repo["pushedAtLocal"] = fmt_warsaw(parse_iso(repo.get("pushedAt")))

    lang_bytes: dict[str, dict[str, Any]] = {}
    for repo in repos:
        for lang in repo["languages"]:
            entry = lang_bytes.setdefault(lang["name"], {"name": lang["name"], "bytes": 0, "color": lang["color"]})
            entry["bytes"] += lang["bytes"]
            if lang.get("color"):
                entry["color"] = lang["color"]
    languages = sorted(lang_bytes.values(), key=lambda x: -x["bytes"])
    total_lang = sum(x["bytes"] for x in languages) or 1
    for lang in languages:
        lang["pct"] = 100.0 * lang["bytes"] / total_lang

    status_counts = {"Live": 0, "Live · in development": 0, "In progress": 0, "Dormant": 0}
    for repo in repos:
        status_counts[repo["status"]] = status_counts.get(repo["status"], 0) + 1

    all_prs = []
    all_issues = []
    all_ahead = []
    failing = []
    for repo in repos:
        for pr in repo["prs"]:
            all_prs.append({**pr, "repo": repo["name"]})
        for issue in repo["issues"]:
            all_issues.append({**issue, "repo": repo["name"]})
        for branch in repo["branches_ahead"]:
            all_ahead.append({**branch, "repo": repo["name"]})
        if (repo.get("ci") or {}).get("conclusion") in {"failure", "timed_out", "startup_failure"}:
            failing.append(
                {
                    "repo": repo["name"],
                    "name": repo["ci"]["name"],
                    "conclusion": repo["ci"]["conclusion"],
                    "url": repo["ci"].get("url"),
                    "createdAt": repo["ci"].get("createdAt"),
                }
            )

    human_prs = [p for p in all_prs if not p.get("dependabot")]
    bot_prs = [p for p in all_prs if p.get("dependabot")]
    live_count = sum(1 for r in repos if r.get("pages_http") == 200)

    return {
        "generated_at": now.astimezone(TZ).strftime("%Y-%m-%d %H:%M:%S"),
        "generated_at_display": now.astimezone(TZ).strftime(f"{now.astimezone(TZ).day} %b %Y, %H:%M"),
        "timezone": "Europe/Warsaw",
        "owner": OWNER,
        "public_only": True,
        "kpis": {
            "repos": len(repos),
            "commits_365": sum(r["commits_365"] for r in repos),
            "commits_90": sum(r["commits_90"] for r in repos),
            "commits_30": sum(r["commits_30"] for r in repos),
            "languages": len(languages),
            "live_pages": live_count,
            "open_prs": sum(r["pr_count"] for r in repos),
            "open_prs_human": len(human_prs),
            "open_prs_dependabot": len(bot_prs),
            "open_issues": sum(r["issue_count"] for r in repos),
            "stars": sum(r["stars"] for r in repos),
        },
        "status_counts": status_counts,
        "languages": languages,
        "weekly": weekly,
        "repos": repos,
        "in_progress": {
            "human_prs": human_prs,
            "dependabot_prs": bot_prs,
            "issues": all_issues,
            "branches_ahead": all_ahead,
            "failing_ci": failing,
        },
        "events": hydrate_event_titles(events, human_prs + bot_prs),
    }


# ---------------------------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------------------------

def svg_open(width: int, height: int, theme: dict[str, str], title: str, desc: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">\n'
        f"<title id=\"title\">{esc(title)}</title>\n"
        f"<desc id=\"desc\">{esc(desc)}</desc>\n"
        f"<rect width=\"{width}\" height=\"{height}\" rx=\"12\" fill=\"{theme['bg']}\" "
        f"stroke=\"{theme['border']}\" stroke-width=\"1\"/>\n"
        f"<style>text{{font-family:{FONT}; font-size:13px; fill:{theme['text']};}} "
        f".muted{{fill:{theme['muted']};}} .faint{{fill:{theme['faint']};}} "
        f".bold{{font-weight:600;}} .title{{font-weight:600; font-size:16px;}}</style>\n"
    )


def svg_close() -> str:
    return "</svg>\n"


def picture_block(base: str, alt: str, cache: str, width: int = SVG_WIDTH) -> str:
    return (
        f"<picture>\n"
        f'  <source media="(prefers-color-scheme: dark)" srcset="dashboard/{base}-dark.svg?v={cache}">\n'
        f'  <img alt="{esc(alt)}" src="dashboard/{base}-light.svg?v={cache}" width="{width}">\n'
        f"</picture>"
    )


def draw_kpis(theme: dict[str, str], snap: dict[str, Any]) -> str:
    k = snap["kpis"]
    items = [
        (str(k["repos"]), "Public repositories"),
        (f"{k['commits_365']:,}", "Commits, 12 months"),
        (str(k["languages"]), "Languages"),
        (str(k["live_pages"]), "Live Pages sites"),
        (str(k["open_prs"]), "Open pull requests"),
        (str(k["open_issues"]), "Open issues"),
        (str(k["stars"]), "Stars"),
        (str(snap["status_counts"]["In progress"]), "In progress"),
    ]
    height = 196
    svg = [svg_open(SVG_WIDTH, height, theme, "Work snapshot", "Key public GitHub figures.")]
    svg.append(f'<text x="24" y="32" class="title">Work snapshot</text>')
    svg.append(
        f'<text x="{SVG_WIDTH-24}" y="32" class="muted" text-anchor="end" font-size="12">'
        f'Data as of {esc(snap["generated_at_display"])} Europe/Warsaw</text>'
    )
    cols = 4
    gap = 12
    left = 20
    top = 50
    card_w = (SVG_WIDTH - left * 2 - gap * (cols - 1)) / cols
    card_h = 58
    for i, (value, label) in enumerate(items):
        r, c = divmod(i, cols)
        x = left + c * (card_w + gap)
        y = top + r * (card_h + gap)
        svg.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{card_w:.1f}" height="{card_h}" rx="8" '
            f'fill="{theme["card"]}" stroke="{theme["border"]}"/>'
        )
        svg.append(
            f'<text x="{x+14:.1f}" y="{y+26:.1f}" class="bold" font-size="20">{esc(value)}</text>'
        )
        svg.append(
            f'<text x="{x+14:.1f}" y="{y+44:.1f}" class="muted" font-size="12">{esc(label)}</text>'
        )
    svg.append(svg_close())
    return "".join(svg)


def draw_activity(theme: dict[str, str], snap: dict[str, Any]) -> str:
    weekly = snap["weekly"]
    height = 230
    svg = [svg_open(SVG_WIDTH, height, theme, "Commit activity, last 12 months", "Weekly commits across public repositories.")]
    svg.append('<text x="24" y="32" class="title">Commit activity · last 12 months</text>')
    weekly_sum = sum(w["total"] for w in weekly)
    svg.append(
        f'<text x="{SVG_WIDTH-24}" y="32" class="muted" text-anchor="end" font-size="12">'
        f'{weekly_sum:,} commits in the 52-week window</text>'
    )
    plot_x, plot_y = 44, 52
    plot_w, plot_h = SVG_WIDTH - 68, 140
    max_v = max((w["total"] for w in weekly), default=0) or 1
    for frac in (0, 0.5, 1):
        y = plot_y + plot_h - plot_h * frac
        svg.append(
            f'<line x1="{plot_x}" y1="{y:.1f}" x2="{plot_x+plot_w}" y2="{y:.1f}" '
            f'stroke="{theme["grid"]}" stroke-width="1"/>'
        )
        svg.append(
            f'<text x="{plot_x-6}" y="{y+4:.1f}" class="faint" font-size="10" text-anchor="end">'
            f'{int(round(max_v * frac))}</text>'
        )
    n = max(len(weekly), 1)
    gap = 2
    bar_w = max(2, (plot_w - gap * (n - 1)) / n)
    for i, week in enumerate(weekly):
        x = plot_x + i * (bar_w + gap)
        h = 0 if max_v == 0 else (week["total"] / max_v) * (plot_h - 2)
        y = plot_y + plot_h - h
        svg.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_w:.2f}" height="{h:.2f}" rx="1.5" fill="{theme["accent"]}">'
            f'<title>{esc(week.get("date") or "")}: {week["total"]} commits</title></rect>'
        )
        if week.get("label"):
            svg.append(
                f'<text x="{x + bar_w/2:.2f}" y="{plot_y+plot_h+16:.1f}" class="faint" '
                f'font-size="10" text-anchor="middle">{esc(week["label"])}</text>'
            )
    svg.append(svg_close())
    return "".join(svg)


def draw_languages(theme: dict[str, str], snap: dict[str, Any]) -> str:
    langs = snap["languages"][:8]
    other = snap["languages"][8:]
    if other:
        langs = langs + [
            {
                "name": "Other",
                "bytes": sum(x["bytes"] for x in other),
                "pct": sum(x["pct"] for x in other),
                "color": theme["faint"],
            }
        ]
    row_h = 28
    height = 64 + row_h * max(len(langs), 1)
    svg = [svg_open(SVG_WIDTH, height, theme, "Languages", "Language breakdown by bytes across public repositories.")]
    svg.append('<text x="24" y="32" class="title">Languages</text>')
    svg.append(
        f'<text x="{SVG_WIDTH-24}" y="32" class="muted" text-anchor="end" font-size="12">'
        f'Shared across {snap["kpis"]["repos"]} public repositories</text>'
    )
    bar_x, bar_w = 170, SVG_WIDTH - 170 - 90
    for i, lang in enumerate(langs):
        y = 50 + i * row_h
        svg.append(f'<text x="24" y="{y+14}" font-size="13">{esc(lang["name"])}</text>')
        svg.append(
            f'<rect x="{bar_x}" y="{y+2}" width="{bar_w}" height="16" rx="4" fill="{theme["card"]}"/>'
        )
        w = max(2, bar_w * (lang["pct"] / 100.0))
        color = lang.get("color") or theme["accent"]
        svg.append(
            f'<rect x="{bar_x}" y="{y+2}" width="{w:.1f}" height="16" rx="4" fill="{esc(color)}"/>'
        )
        svg.append(
            f'<text x="{bar_x+bar_w+10}" y="{y+14}" class="muted" font-size="12">{lang["pct"]:.1f}%</text>'
        )
    svg.append(svg_close())
    return "".join(svg)


def draw_status(theme: dict[str, str], snap: dict[str, Any]) -> str:
    counts = snap["status_counts"]
    order = [
        ("In progress", theme["warning"], theme["warning_bg"]),
        ("Shipped/live", theme["success"], theme["success_bg"]),
        ("Dormant", theme["muted"], theme["card"]),
    ]
    total = max(sum(counts.values()), 1)
    height = 196
    svg = [svg_open(SVG_WIDTH, height, theme, "Project status", "Shipped, in progress, and dormant public repositories.")]
    svg.append('<text x="24" y="32" class="title">Project status</text>')
    svg.append(
        f'<text x="{SVG_WIDTH-24}" y="32" class="muted" text-anchor="end" font-size="12">'
        f'{total} public repositories</text>'
    )
    # Stacked bar (clipped so a single segment keeps the rounded caps)
    x, y, w, h = 24, 52, SVG_WIDTH - 48, 22
    svg.append(f'<defs><clipPath id="statusbar"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6"/></clipPath></defs>')
    svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{theme["card"]}"/>')
    cursor = x
    segs = [(label, color, bg, counts[label]) for label, color, bg in order if counts[label]]
    for i, (label, color, _bg, n) in enumerate(segs):
        sw = w * (n / total)
        if i == len(segs) - 1:
            sw = x + w - cursor
        svg.append(
            f'<rect x="{cursor:.1f}" y="{y}" width="{sw:.1f}" height="{h}" fill="{color}" clip-path="url(#statusbar)"/>'
        )
        cursor += sw

    card_w = (SVG_WIDTH - 48 - 24) / 3
    for i, (label, color, bg) in enumerate(order):
        cx = 24 + i * (card_w + 12)
        cy = 92
        n = counts[label]
        svg.append(
            f'<rect x="{cx}" y="{cy}" width="{card_w}" height="80" rx="8" fill="{bg}" stroke="{theme["border"]}"/>'
        )
        svg.append(f'<circle cx="{cx+18}" cy="{cy+22}" r="5" fill="{color}"/>')
        svg.append(f'<text x="{cx+30}" y="{cy+27}" class="bold">{esc(label)}</text>')
        svg.append(f'<text x="{cx+18}" y="{cy+58}" class="bold" font-size="22">{n}</text>')
    svg.append(svg_close())
    return "".join(svg)


def draw_list_svg(
    theme: dict[str, str],
    title: str,
    desc: str,
    sections: list[tuple[str, list[str]]],
    empty: str,
) -> str:
    # Measure height from wrapped lines.
    line_h = 18
    header_h = 46
    section_h = 26
    pad_bottom = 20
    body_lines = 0
    for _title, rows in sections:
        body_lines += 1 + max(len(rows), 1)
    height = header_h + body_lines * line_h + len(sections) * 10 + pad_bottom
    height = max(height, 120)
    svg = [svg_open(SVG_WIDTH, height, theme, title, desc)]
    svg.append(f'<text x="24" y="32" class="title">{esc(title)}</text>')
    y = 58
    any_row = False
    for heading, rows in sections:
        svg.append(f'<text x="24" y="{y}" class="bold" font-size="13">{esc(heading)}</text>')
        y += line_h
        if not rows:
            svg.append(f'<text x="24" y="{y}" class="muted" font-size="12">{esc(empty)}</text>')
            y += line_h + 8
            continue
        any_row = True
        for row in rows:
            svg.append(f'<text x="24" y="{y}" font-size="12">{esc(row)}</text>')
            y += line_h
        y += 8
    if not any_row and not sections:
        svg.append(f'<text x="24" y="64" class="muted">{esc(empty)}</text>')
    svg.append(svg_close())
    return "".join(svg)


def in_progress_sections(snap: dict[str, Any]) -> list[tuple[str, list[str]]]:
    ip = snap["in_progress"]
    human = ip.get("human_prs") or []
    bots = ip.get("dependabot_prs")
    if bots is None:
        bots = []
        for repo, n in (ip.get("dependabot_by_repo") or {}).items():
            bots.extend({"repo": repo, "number": 0, "title": "", "author": "dependabot[bot]", "isDraft": False, "dependabot": True} for _ in range(int(n)))
    issues = ip.get("issues") or []
    branches = ip.get("branches_ahead") or []
    failing = ip.get("failing_ci") or []

    def pr_line(pr: dict[str, Any]) -> str:
        flag = "draft · " if pr.get("isDraft") else ""
        return truncate(
            f"{pr['repo']}#{pr['number']} · {flag}{pr['title']} ({pr['author']})",
            118,
        )

    human_rows = [pr_line(pr) for pr in sorted(human, key=lambda p: (p["repo"], p["number"]))]
    # Dependabot: compact per-repo counts, not every title.
    bot_counts: dict[str, int] = {}
    for pr in bots:
        bot_counts[pr["repo"]] = bot_counts.get(pr["repo"], 0) + 1
    if bots:
        bot_rows = [
            f"{repo} — {n} open"
            for repo, n in sorted(bot_counts.items(), key=lambda x: (-x[1], x[0]))
        ]
    else:
        bot_rows = []

    issue_rows = [
        truncate(f"{iss['repo']}#{iss['number']} · {iss['title']} ({iss['author']})", 118)
        for iss in issues
    ]
    branch_rows = [
        truncate(
            f"{b['repo']}/{b['name']} · {b['ahead']} commit{'s' if b['ahead'] != 1 else ''} ahead"
            + (f", {b['behind']} behind" if b.get("behind") else ""),
            118,
        )
        for b in branches
    ]
    fail_rows = [
        truncate(f"{f['repo']} · {f['name']} ({f['conclusion']})", 118) for f in failing
    ]

    sections = [
        (f"Open pull requests — {len(human)} in hand", human_rows or ["None."]),
        (f"Dependabot — {len(bots)} open", bot_rows or ["None."]),
        (f"Open issues — {len(issues)}", issue_rows or ["None."]),
        (f"Branches ahead of the default branch — {len(branches)}", branch_rows or ["None."]),
        (f"Failing latest workflows — {len(failing)}", fail_rows or ["None."]),
    ]
    return sections


def hydrate_event_titles(events: list[dict[str, Any]], prs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fill PR titles omitted from the public Events API using known open PRs."""
    lookup: dict[tuple[str, int], dict[str, Any]] = {}
    for pr in prs:
        try:
            lookup[(pr["repo"], int(pr["number"]))] = pr
        except (KeyError, TypeError, ValueError):
            continue
    for ev in events:
        if ev.get("type") != "pr" or ev.get("number") is None:
            continue
        info = lookup.get((ev.get("repo"), int(ev["number"])))
        if not info:
            continue
        if not ev.get("title"):
            ev["title"] = info.get("title") or ""
        if ev.get("draft") is None:
            ev["draft"] = bool(info.get("isDraft"))
        if info.get("url"):
            ev["url"] = ev.get("url") or info["url"]
    return events


def event_line(ev: dict[str, Any]) -> str:
    when = fmt_warsaw(parse_iso(ev.get("createdAt")))
    if ev["type"] == "push":
        branch = ev.get("branch") or "default"
        n = ev.get("commits")
        head = (ev.get("head") or "")[:7]
        if ev.get("messages"):
            detail = ev["messages"][0]
        elif isinstance(n, int):
            detail = f"{n} commit" + ("" if n == 1 else "s")
        elif head:
            detail = head
        else:
            detail = ""
        core = f"{when}  {ev['repo']}  pushed to {branch}"
        if detail:
            core += f" — {detail}"
        return truncate(core, 124)
    action = ev.get("action") or "updated"
    draft = "draft " if ev.get("draft") else ""
    title = ev.get("title") or ""
    line = f"{when}  {ev['repo']}  {action} {draft}PR #{ev.get('number')}"
    if title:
        line += f" — {title}"
    return truncate(line, 124)


def write_svg(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def md_escape(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ")


def status_badge(status: str, cache: str) -> str:
    slug = {"In progress": "in-progress", "Shipped/live": "shipped", "Dormant": "dormant"}[status]
    alt = status
    # A single solid badge reads on both themes.
    return f'<img src="dashboard/badge-{slug}.svg?v={cache}" alt="{alt}" height="20">'


def build_readme_block(snap: dict[str, Any]) -> str:
    cache = datetime.strptime(snap["generated_at"], "%Y-%m-%d %H:%M:%S").strftime("%Y%m%d%H%M")
    k = snap["kpis"]
    lines: list[str] = [
        README_START,
        "<!-- Generated by scripts/collect_dashboard.py. Do not edit this block by hand. -->",
        "",
        "## Work dashboard",
        "",
        "A live view of public GitHub work — what is shipped, and what is still open. "
        "Figures come from the GitHub API and refresh automatically every six hours. "
        "Private repositories are not included.",
        "",
        f"**Data as of {snap['generated_at_display']} Europe/Warsaw.** "
        f"{k['repos']} public repositories · {k['commits_365']:,} commits in the last 12 months · "
        f"{k['live_pages']} live Pages sites · {k['open_prs']} open pull requests "
        f"({k['open_prs_human']} in hand, {k['open_prs_dependabot']} Dependabot) · "
        f"{k['open_issues']} open issues.",
        "",
        picture_block("kpis", "Work snapshot: repository, commit, Pages, pull request and issue counts", cache),
        "",
        picture_block("activity", "Weekly commit activity across public repositories, last 12 months", cache),
        "",
        picture_block("languages", "Language breakdown across public repositories", cache),
        "",
        picture_block("status", "Repositories by status: in progress, shipped/live, or dormant", cache),
        "",
        "A repository is marked **In progress** if it was pushed in the last 14 days, or if it has "
        "open or draft pull requests, a non-Dependabot branch ahead of the default branch, or a failing "
        "latest workflow. **Shipped/live** means the GitHub Pages site returned HTTP 200 and none of "
        "those in-progress signals apply. **Dormant** means neither. "
        f"All {k['live_pages']} public Pages sites currently return HTTP 200"
        + (
            f", and because every repository was pushed in the last {IN_PROGRESS_DAYS} days, "
            "all of them are classified as In progress under that rule."
            if snap["status_counts"].get("In progress") == k["repos"] and k["live_pages"] == k["repos"]
            else "."
        ),
        "",
        picture_block("in-progress", "Open pull requests, issues, branches ahead, and failing workflows", cache),
        "",
        picture_block("recent", "Recent public pushes and pull request events", cache),
        "",
        "### Public repositories",
        "",
        "| Project | Status | Live site | Language | Last push (Europe/Warsaw) | 30d | 90d | PRs | Issues | CI | Description |",
        "| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for repo in sorted(snap["repos"], key=lambda r: r["name"].lower()):
        live = repo["live_label"]
        if repo.get("pages_url") and live == "Live":
            live_cell = f"[Live]({repo['pages_url']})"
        elif repo.get("pages_url") and live not in {"No Pages"}:
            live_cell = f"[{md_escape(live)}]({repo['pages_url']})"
        else:
            live_cell = md_escape(live)
        desc = truncate(repo.get("description") or "—", 90)
        name_cell = f"[{repo['name']}]({repo['url']})"
        ci = md_escape(repo["ci_label"])
        if repo.get("ci") and repo["ci"].get("url"):
            ci = f"[{ci}]({repo['ci']['url']})"
        lines.append(
            "| "
            + " | ".join(
                [
                    name_cell,
                    status_badge(repo["status"], cache),
                    live_cell,
                    md_escape(repo.get("primaryLanguage") or repo.get("language") or "—"),
                    md_escape(repo["pushedAtLocal"]),
                    str(repo["commits_30"]),
                    str(repo["commits_90"]),
                    str(repo["pr_count"]),
                    str(repo["issue_count"]),
                    ci,
                    md_escape(desc),
                ]
            )
            + " |"
        )
    lines += [
        "",
        "Commit counts are measured on each repository’s default branch. "
        "The dashboard is generated by [`scripts/collect_dashboard.py`](scripts/collect_dashboard.py) "
        "and [this workflow](.github/workflows/update-dashboard.yml).",
        "",
        README_END,
    ]
    return "\n".join(lines) + "\n"


def patch_readme(root: Path, block: str) -> None:
    path = root / "README.md"
    text = path.read_text(encoding="utf-8")
    start = text.find(README_START)
    end = text.find(README_END)
    if start != -1 and end != -1 and end > start:
        end += len(README_END)
        # Keep a single trailing newline around the block.
        new = text[:start].rstrip() + "\n\n" + block.rstrip() + "\n\n" + text[end:].lstrip()
        if not new.endswith("\n"):
            new += "\n"
        path.write_text(new, encoding="utf-8")
        return
    # Insert before Education, or append.
    marker = "## Education"
    idx = text.find(marker)
    if idx != -1:
        new = text[:idx].rstrip() + "\n\n" + block.rstrip() + "\n\n" + text[idx:]
    else:
        new = text.rstrip() + "\n\n" + block.rstrip() + "\n"
    if not new.endswith("\n"):
        new += "\n"
    path.write_text(new, encoding="utf-8")


def draw_badges() -> dict[str, str]:
    specs = {
        "in-progress": ("In progress", "#9a6700", "#fff8c5", "#9a6700"),
        "shipped": ("Shipped/live", "#1a7f37", "#dafbe1", "#1a7f37"),
        "dormant": ("Dormant", "#656d76", "#f6f8fa", "#d0d7de"),
    }
    out: dict[str, str] = {}
    for slug, (label, fg, bg, border) in specs.items():
        # Approximate text width for a compact shields-style pill.
        w = 10 + int(len(label) * 7.2) + 10
        h = 20
        out[slug] = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}">'
            f"<title>{esc(label)}</title>"
            f'<rect width="{w}" height="{h}" rx="10" fill="{bg}" stroke="{border}"/>'
            f'<text x="{w/2:.1f}" y="14.5" text-anchor="middle" '
            f'font-family="ui-sans-serif, system-ui, sans-serif" font-size="11" font-weight="600" fill="{fg}">{esc(label)}</text>'
            f"</svg>\n"
        )
    return out


def write_all_svgs(root: Path, snap: dict[str, Any]) -> None:
    dash = root / "dashboard"
    dash.mkdir(parents=True, exist_ok=True)
    recent_rows = [event_line(ev) for ev in snap["events"]] or ["No public push or pull-request events in the fetched window."]
    for theme in (LIGHT, DARK):
        write_svg(dash / f"kpis-{theme['name']}.svg", draw_kpis(theme, snap))
        write_svg(dash / f"activity-{theme['name']}.svg", draw_activity(theme, snap))
        write_svg(dash / f"languages-{theme['name']}.svg", draw_languages(theme, snap))
        write_svg(dash / f"status-{theme['name']}.svg", draw_status(theme, snap))
        write_svg(
            dash / f"in-progress-{theme['name']}.svg",
            draw_list_svg(
                theme,
                "Still open",
                "Open pull requests, issues, branches ahead of default, and failing workflows.",
                in_progress_sections(snap),
                "None.",
            ),
        )
        write_svg(
            dash / f"recent-{theme['name']}.svg",
            draw_list_svg(
                theme,
                "Recent activity",
                "Latest public pushes and pull request events.",
                [(f"Last {len(snap['events'])} public pushes and pull requests", recent_rows)],
                "No recent public push or pull-request events.",
            ),
        )
    for slug, svg in draw_badges().items():
        write_svg(dash / f"badge-{slug}.svg", svg)


def public_data(snap: dict[str, Any]) -> dict[str, Any]:
    """A compact, public-safe JSON snapshot (no tokens, no private repos)."""
    repos = []
    for r in snap["repos"]:
        repos.append(
            {
                "name": r["name"],
                "url": r["url"],
                # Override any repo description that would leak a venue address or similar.
                "description": {
                    "kingdom-life-krakow": "Public English-language church website.",
                }.get(r["name"], r["description"]),
                "language": r["primaryLanguage"],
                "pushedAt": r["pushedAt"],
                "pushedAtLocal": r["pushedAtLocal"],
                "commits_30": r["commits_30"],
                "commits_90": r["commits_90"],
                "commits_365": r["commits_365"],
                "pages_url": r.get("pages_url"),
                "pages_http": r.get("pages_http"),
                "live_label": r["live_label"],
                "pr_count": r["pr_count"],
                "issue_count": r["issue_count"],
                "ci_label": r["ci_label"],
                "status": r["status"],
                "stars": r["stars"],
            }
        )
    return {
        "generated_at": snap["generated_at"],
        "timezone": snap["timezone"],
        "public_only": True,
        "kpis": snap["kpis"],
        "status_counts": snap["status_counts"],
        "languages": snap["languages"],
        "weekly": snap["weekly"],
        "repos": repos,
        "in_progress": {
            "human_pr_count": len(snap["in_progress"]["human_prs"]),
            "dependabot_pr_count": len(snap["in_progress"]["dependabot_prs"]),
            "human_prs": [
                {
                    "repo": p["repo"],
                    "number": p["number"],
                    "title": p["title"],
                    "url": p["url"],
                    "isDraft": p["isDraft"],
                    "author": p["author"],
                }
                for p in snap["in_progress"]["human_prs"]
            ],
            "dependabot_by_repo": _count_by(snap["in_progress"]["dependabot_prs"], "repo"),
            "issues": snap["in_progress"]["issues"],
            "branches_ahead": snap["in_progress"]["branches_ahead"],
            "failing_ci": snap["in_progress"]["failing_ci"],
        },
        "events": snap["events"],
    }


def _count_by(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for item in items:
        out[item[key]] = out.get(item[key], 0) + 1
    return out


def main() -> int:
    root = repo_root()
    now = datetime.now(TZ)
    print(f"Collecting public GitHub data for {OWNER} at {fmt_warsaw(now)} Europe/Warsaw…", flush=True)
    gh = GitHub(load_token())
    repos = collect_repos(gh, now)
    print(f"  {len(repos)} public repositories", flush=True)

    # Enrich sequentially enough to stay polite, but overlap HTTP / compare calls
    # across repositories.
    def _enrich(repo: dict[str, Any]) -> dict[str, Any]:
        print(f"  enrich {repo['name']}", flush=True)
        return enrich_repo(gh, repo)

    enriched: list[dict[str, Any]] = []
    # Keep this modest: compare calls already fan out per branch inside enrich_repo.
    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = {pool.submit(_enrich, repo): repo["name"] for repo in repos}
        for fut in as_completed(futs):
            name = futs[fut]
            try:
                enriched.append(fut.result())
            except Exception as exc:  # noqa: BLE001 — surface and continue
                print(f"  warning: failed to enrich {name}: {exc}", file=sys.stderr, flush=True)
                # Keep the base record so the dashboard still lists the repo.
                base = next(r for r in repos if r["name"] == name)
                base.setdefault("pages", {"enabled": False, "html_url": pages_url_for(base), "status": None, "source": None})
                base["pages_url"] = base["pages"]["html_url"]
                base["pages_http"] = None
                base["ci"] = None
                base["branches_ahead"] = []
                enriched.append(base)

    enriched.sort(key=lambda r: r["name"].lower())
    print("  weekly activity…", flush=True)
    weekly = collect_weekly_activity(gh, enriched, now)
    print("  public events…", flush=True)
    events = collect_events(gh, limit=30)
    snap = build_snapshot(enriched, weekly, events, now)

    dash = root / "dashboard"
    dash.mkdir(parents=True, exist_ok=True)
    (dash / "data.json").write_text(
        json.dumps(public_data(snap), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parent))
    from render_site import write_site
    write_site(root, snap)
    k = snap["kpis"]
    sc = snap["status_counts"]
    print(
        f"Done. {k['repos']} public repos · {k['commits_365']} commits/12mo · "
        f"{k['live_pages']} live · {k['open_prs']} open PRs · "
        f"status {sc} · wrote dashboard/ and README.md",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
