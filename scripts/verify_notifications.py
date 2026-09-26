import asyncio
import json
import urllib.request

from playwright.async_api import async_playwright

BASE = "http://localhost:3001"


def api(path, data=None, token=None, method=None):
    req = urllib.request.Request("http://localhost:5000/api" + path, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    body = json.dumps(data).encode() if data is not None else None
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, body) as resp:
        return json.loads(resp.read())


async def main():
    # 用已有测试账号 B（有一条未读点赞通知）
    login = api("/users/login", {"email": "notif_actor@test.local", "password": "test123456"})
    token = login["data"]["token"]
    user = login["data"]["user"]

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        errors = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))

        await page.goto(BASE + "/", wait_until="domcontentloaded")
        await page.evaluate(
            """({token, user}) => {
                localStorage.setItem('token', token);
                localStorage.setItem('userInfo', JSON.stringify(user));
            }""",
            {"token": token, "user": user},
        )
        await page.reload(wait_until="networkidle")
        await page.wait_for_timeout(1500)
        # 打开通知面板
        await page.locator('button[title="通知"]').click()
        await page.wait_for_timeout(800)
        await page.screenshot(path="docs/screenshots/notifications-light.png")

        print("console errors:", errors if errors else "NONE")
        await browser.close()


asyncio.run(main())
