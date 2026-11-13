#!/usr/bin/env python3
"""Render local GitHub-like previews of README.md (light and dark).

Writes preview-light.html / preview-dark.html and preview-light.png / preview-dark.png
at the repository root. Those files are gitignored and are not published.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

# Prefer a venv with markdown if present.
for candidate in ("/tmp/mdvenv/bin/python", sys.executable):
    if Path(candidate).exists():
        # We import markdown in-process; if missing, re-exec the venv python.
        try:
            import markdown as _md  # noqa: F401
            break
        except ImportError:
            if candidate != sys.executable:
                os.execv(candidate, [candidate, *sys.argv])
else:
    pass

import markdown
import websockets

ROOT = Path(__file__).resolve().parents[1]
CSS_LIGHT = Path("/tmp/ghmcss/github-markdown-light.css")
CSS_DARK = Path("/tmp/ghmcss/github-markdown-dark.css")
PORT = 9333
WIDTH = 1012


def md_to_html(text: str) -> str:
    # GitHub-flavored tables, raw HTML kept, no typographic substitutions.
    return markdown.markdown(
        text,
        extensions=["tables", "fenced_code", "sane_lists"],
        output_format="html",
    )


def build_html(body: str, theme: str) -> str:
    css_path = CSS_DARK if theme == "dark" else CSS_LIGHT
    css = css_path.read_text(encoding="utf-8")
    if theme == "dark":
        page_bg = "#0d1117"
        article_bg = "#0d1117"
        border = "#30363d"
        color_scheme = "dark"
    else:
        page_bg = "#f6f8fa"
        article_bg = "#ffffff"
        border = "#d0d7de"
        color_scheme = "light"
    return f"""<!DOCTYPE html>
<html lang="en" data-color-mode="{theme}" style="color-scheme:{color_scheme}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Arnold-RG profile README ({theme})</title>
<style>
{css}
html, body {{
  margin: 0;
  padding: 0;
  background: {page_bg};
  color-scheme: {color_scheme};
}}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
}}
.frame {{
  width: 1012px;
  margin: 0 auto;
  padding: 0;
}}
.markdown-body {{
  box-sizing: border-box;
  width: 1012px;
  background: {article_bg};
  border: none;
  padding: 32px 32px 48px;
}}
.markdown-body img {{
  max-width: 100%;
  height: auto;
  background: transparent;
}}
.markdown-body table {{
  display: block;
  overflow-x: auto;
}}
</style>
</head>
<body>
  <div class="frame">
    <article class="markdown-body">{body}</article>
  </div>
</body>
</html>
"""


def write_html() -> tuple[Path, Path]:
    source = (ROOT / "README.md").read_text(encoding="utf-8")
    body = md_to_html(source)
    light = ROOT / "preview-light.html"
    dark = ROOT / "preview-dark.html"
    light.write_text(build_html(body, "light"), encoding="utf-8")
    dark.write_text(build_html(body, "dark"), encoding="utf-8")
    return light, dark


class Chrome:
    def __init__(self, port: int = PORT) -> None:
        self.port = port
        self.proc: subprocess.Popen | None = None
        self.user_dir = Path("/tmp/chrome-profile-preview")
        self.user_dir.mkdir(exist_ok=True)

    def start(self) -> None:
        self.proc = subprocess.Popen(
            [
                "google-chrome-stable",
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--hide-scrollbars",
                "--disable-extensions",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-background-networking",
                f"--remote-debugging-port={self.port}",
                "--remote-allow-origins=*",
                f"--user-data-dir={self.user_dir}",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.time() + 15
        last_err = None
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json/version", timeout=1) as resp:
                    json.load(resp)
                    return
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                time.sleep(0.15)
        raise SystemExit(f"Chrome DevTools did not start: {last_err}")

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()

    def ws_url(self) -> str:
        # Prefer PUT /json/new (newer Chrome rejects GET), then fall back to an existing tab.
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/json/new?about:blank", method="PUT"
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.load(resp)
            return data["webSocketDebuggerUrl"]
        except Exception:
            with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json/list", timeout=5) as resp:
                tabs = json.load(resp)
            for tab in tabs:
                if tab.get("webSocketDebuggerUrl"):
                    return tab["webSocketDebuggerUrl"]
            raise SystemExit(f"No Chrome DevTools tab available: {tabs!r}")


async def call(ws, mid: int, method: str, params: dict | None = None, timeout: float = 20.0):
    await ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
    loop = asyncio.get_event_loop()
    end = loop.time() + timeout
    while True:
        remaining = end - loop.time()
        if remaining <= 0:
            raise TimeoutError(method)
        raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
        msg = json.loads(raw)
        if msg.get("id") == mid:
            if "error" in msg:
                raise RuntimeError(f"{method}: {msg['error']}")
            return msg.get("result", {})


async def screenshot(ws_url: str, url: str, dest: Path, scheme: str) -> None:
    async with websockets.connect(ws_url, max_size=32 * 1024 * 1024) as ws:
        mid = 0

        async def c(method, params=None, timeout=30.0):
            nonlocal mid
            mid += 1
            return await call(ws, mid, method, params, timeout=timeout)

        await c("Page.enable")
        await c("Runtime.enable")
        await c(
            "Emulation.setEmulatedMedia",
            {"media": "screen", "features": [{"name": "prefers-color-scheme", "value": scheme}]},
        )
        await c(
            "Emulation.setDeviceMetricsOverride",
            {"width": WIDTH, "height": 900, "deviceScaleFactor": 2, "mobile": False},
        )
        await c("Page.navigate", {"url": url})
        # Wait until load, then for images/SVGs.
        for _ in range(40):
        # Poll readyState
            state = await c("Runtime.evaluate", {"expression": "document.readyState", "returnByValue": True})
            if (state.get("result") or {}).get("value") == "complete":
                break
            await asyncio.sleep(0.1)
        await asyncio.sleep(0.4)
        await c(
            "Runtime.evaluate",
            {
                "expression": "Promise.all(Array.from(document.images).map(img => img.complete ? null : new Promise(r => { img.addEventListener('load', r, {once:true}); img.addEventListener('error', r, {once:true}); })))",
                "awaitPromise": True,
                "returnByValue": True,
            },
            timeout=30.0,
        )
        await asyncio.sleep(1.2)
        height = await c(
            "Runtime.evaluate",
            {
                "expression": "Math.ceil(Math.max(document.body.scrollHeight, document.documentElement.scrollHeight, document.body.offsetHeight))",
                "returnByValue": True,
            },
        )
        px = int((height.get("result") or {}).get("value") or 2000)
        px = min(max(px + 24, 800), 20000)
        await c(
            "Emulation.setDeviceMetricsOverride",
            {"width": WIDTH, "height": px, "deviceScaleFactor": 2, "mobile": False},
        )
        await asyncio.sleep(0.3)
        shot = await c(
            "Page.captureScreenshot",
            {"format": "png", "captureBeyondViewport": True, "fromSurface": True},
            timeout=60.0,
        )
        dest.write_bytes(base64.b64decode(shot["data"]))
        print(f"wrote {dest} ({dest.stat().st_size} bytes, {px}px tall)", flush=True)


async def main() -> int:
    _light, dark = write_html()
    dest = ROOT / "preview-dark-v2.png"
    top = ROOT / "preview-top-v2.png"
    # Keep a matching HTML next to the PNG (gitignored).
    preview_html = ROOT / "preview-dark-v2.html"
    preview_html.write_text(dark.read_text(encoding="utf-8"), encoding="utf-8")
    chrome = Chrome()
    chrome.start()
    try:
        await screenshot(chrome.ws_url(), preview_html.resolve().as_uri(), dest, "dark")
    finally:
        chrome.stop()
    try:
        from PIL import Image
    except ImportError:
        import subprocess, sys
        subprocess.check_call([sys.executable.replace("mdvenv/bin/python", "bin/python3") if False else "/usr/bin/python3", "-c",
            "from PIL import Image; from pathlib import Path; d=Path(%r); t=Path(%r); im=Image.open(d); h=min(im.height, 1150*2); im.crop((0,0,im.width,h)).save(t, optimize=True); print(h)" % (str(dest), str(top))])
        return 0
    im = Image.open(dest)
    crop_h = min(im.height, 1150 * 2)
    im.crop((0, 0, im.width, crop_h)).save(top, optimize=True)
    print(f"wrote {top} ({top.stat().st_size} bytes, {crop_h}px tall crop)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
