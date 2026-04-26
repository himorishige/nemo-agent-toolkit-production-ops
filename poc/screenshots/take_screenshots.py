"""Capture Langfuse UI screenshots for the Zenn Book.

Uses the existing headless_shell-1208 binary that ships with playwright,
because the chromium-1217 binary fails on this machine with an ICU error.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from playwright.async_api import async_playwright

OUTPUT_DIR = Path("/home/morishige/works/zenn-contents/images/nemo-agent-toolkit-production-ops")
HOST = "http://localhost:3000"
EMAIL = "poc@example.local"
PASSWORD = os.environ.get("LF_PASSWORD", "")
EXECUTABLE_PATH = "/home/morishige/.cache/ms-playwright/chromium_headless_shell-1208/chrome-linux/headless_shell"

PAGES: list[tuple[str, str]] = [
    ("01-traces-list", "/project/poc-project/traces"),
    ("02-prompts-list", "/project/poc-project/prompts"),
    ("03-datasets-list", "/project/poc-project/datasets"),
    ("04-models-list", "/project/poc-project/models"),
    ("05-dashboard", "/project/poc-project/dashboards"),
]


async def main() -> None:
    if not PASSWORD:
        sys.exit("LF_PASSWORD environment variable is required")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=EXECUTABLE_PATH,
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        # Sign in
        await page.goto(f"{HOST}/auth/sign-in", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        await page.get_by_placeholder("jsdoe@example.com").fill(EMAIL)
        await page.get_by_label("Password").fill(PASSWORD)
        await page.get_by_role("button", name="Sign in").click()
        # ログイン成功後はトップ（"/"）に飛ぶ場合と project 配下に飛ぶ場合がある
        await asyncio.sleep(3)
        print(f"Signed in: {page.url}")

        for name, path in PAGES:
            url = f"{HOST}{path}"
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            except Exception as e:
                print(f"[warn] {name}: {url} navigate failed: {e}")
            # Allow tables / charts to render
            await asyncio.sleep(2)
            target = OUTPUT_DIR / f"{name}.png"
            await page.screenshot(path=str(target), full_page=False)
            print(f"saved {target}")

        # 最近の trace を 1 件取り出して詳細画面へ
        import requests
        from base64 import b64encode

        pk = "pk-lf-poc-public-417a81c251fe3fba"
        sk = "sk-lf-poc-secret-8623b38cba8225bb206b44e7a67433ab"
        auth = b64encode(f"{pk}:{sk}".encode()).decode()
        r = requests.get(
            f"{HOST}/api/public/traces?projectId=poc-project&limit=3",
            headers={"Authorization": f"Basic {auth}"},
            timeout=10,
        )
        traces = r.json().get("data", [])
        if traces:
            trace_id = traces[0]["id"]
            await page.goto(f"{HOST}/project/poc-project/traces/{trace_id}", wait_until="domcontentloaded")
            await asyncio.sleep(4)
            await page.screenshot(path=str(OUTPUT_DIR / "06-trace-detail.png"), full_page=False)
            print(f"saved 06-trace-detail.png (trace {trace_id[:8]}...)")

        # Prompt 詳細（v1）
        await page.goto(f"{HOST}/project/poc-project/prompts/internal-qa-system", wait_until="domcontentloaded")
        await asyncio.sleep(3)
        await page.screenshot(path=str(OUTPUT_DIR / "07-prompt-detail.png"), full_page=False)
        print("saved 07-prompt-detail.png")

        # Dataset 詳細
        await page.goto(f"{HOST}/project/poc-project/datasets", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        ds_link = page.locator("a:has-text('internal-qa-eval-v1')").first
        if await ds_link.count() > 0:
            await ds_link.click()
            await asyncio.sleep(3)
            await page.screenshot(path=str(OUTPUT_DIR / "08-dataset-detail.png"), full_page=False)
            print("saved 08-dataset-detail.png")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
