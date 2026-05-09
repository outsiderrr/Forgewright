"""Capture PR-quality screenshots against the real baseline_011 batch.

Run manually (NOT part of pytest):

    .venv/bin/python tools/review_ui/tests/_capture_pr_screenshots.py

Saves into ``tools/review_ui/tests/_screenshots_pr/``.  These are the
images that go into the T-3.6a PR description (v1.0 F16 mandatory).
"""
from __future__ import annotations

import socket
import threading
import time
from pathlib import Path

import uvicorn
from playwright.sync_api import sync_playwright

from tools.review_ui.server import build_app


REPO = Path(__file__).resolve().parents[3]
BATCH = REPO / "generator" / "experiments" / "20260506T113419Z_baseline_011"
SCENES = REPO / "content"
OUT = Path(__file__).resolve().parent / "_screenshots_pr"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if not BATCH.is_dir():
        raise SystemExit(f"baseline batch missing: {BATCH}")

    app = build_app(batch_dir=BATCH, scenes_dir=SCENES)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(50):
        if server.started:
            break
        time.sleep(0.1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        page.goto(f"http://127.0.0.1:{port}/")
        page.wait_for_selector("#scene-list .scene-row", timeout=10_000)

        # 1. scene list (full app first paint)
        page.screenshot(path=str(OUT / "01_scene_list.png"), full_page=False)

        # 2. mermaid graph view of scene 0
        page.click("text=waystation_of_iron_oath__iter00")
        page.wait_for_selector("#graph-container svg", timeout=10_000)
        page.wait_for_timeout(400)  # let mermaid finish layout
        page.screenshot(path=str(OUT / "02_graph_mermaid.png"), full_page=False)

        # 3. validator topology tab
        page.click("#validator-tabs .tab[data-tab='topology']")
        page.wait_for_timeout(150)
        page.screenshot(path=str(OUT / "03_validator_topology.png"), full_page=False)

        # 4. dependencies + advisory + A/R/S
        page.click("#main-tabs .tab[data-tab='deps']")
        page.click("#validator-tabs .tab[data-tab='sampling']")
        page.fill("#reject-reason", "（示例：本场景节奏偏快，缺一个回合让玩家消化新信息）")
        page.wait_for_timeout(150)
        page.screenshot(path=str(OUT / "04_review_ars.png"), full_page=False)

        # 5. ASCII fallback view (F17 visual)
        page.click("#main-tabs .tab[data-tab='graph']")
        page.click(".format-btn[data-format='ascii']")
        page.wait_for_selector("#graph-container pre", timeout=5_000)
        page.wait_for_timeout(200)
        page.screenshot(path=str(OUT / "05_graph_ascii_fallback.png"), full_page=False)

        # 6. nodes view (text excerpts)
        page.click("#main-tabs .tab[data-tab='nodes']")
        page.wait_for_timeout(150)
        page.screenshot(path=str(OUT / "06_nodes.png"), full_page=False)

        browser.close()

    server.should_exit = True
    print(f"wrote 6 screenshots to {OUT}")


if __name__ == "__main__":
    main()
