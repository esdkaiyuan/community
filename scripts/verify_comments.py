import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        errors = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))

        await page.goto("http://localhost:3001/project/19", wait_until="networkidle")
        await page.wait_for_timeout(1200)
        # 滚动到评论区
        await page.locator("h2", has_text="评论").first.scroll_into_view_if_needed()
        await page.wait_for_timeout(1500)
        await page.screenshot(path="docs/screenshots/comments-light.png", full_page=False)

        # 深色模式
        dark = await browser.new_page(viewport={"width": 1440, "height": 900}, color_scheme="dark")
        dark.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        dark.on("pageerror", lambda e: errors.append(str(e)))
        await dark.goto("http://localhost:3001/project/19", wait_until="networkidle")
        await dark.wait_for_timeout(1200)
        await dark.locator("h2", has_text="评论").first.scroll_into_view_if_needed()
        await dark.wait_for_timeout(1500)
        await dark.screenshot(path="docs/screenshots/comments-dark.png", full_page=False)

        print("console errors:", errors if errors else "NONE")
        await browser.close()

asyncio.run(main())
