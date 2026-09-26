import asyncio
import json
import urllib.request

from playwright.async_api import async_playwright

BASE = "http://localhost:3001"


def api(path, data=None, token=None):
    req = urllib.request.Request("http://localhost:5000/api" + path)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    body = json.dumps(data).encode() if data is not None else None
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, body) as resp:
        return json.loads(resp.read())


async def main():
    # 造数：注册临时用户 + 1 根评论 + 2 回复
    reg = api("/users/register", {"username": "ui_reply_demo", "email": "ui_reply_demo@test.local", "password": "test123456"})
    token = reg["data"]["token"]
    user = reg["data"]["user"]
    root = api("/projects/19/comments", {"content": "两级结构展示：根评论外观与 App Store 评价列表一致。"}, token)["data"]["comment"]["id"]
    api("/projects/19/comments", {"content": "回复展示在缩进线上，头像小一号。", "parentId": root}, token)
    api("/projects/19/comments", {"content": "回复回复会自动展平到根评论下。", "parentId": root}, token)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        errors = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))

        await page.goto(BASE + "/project/19", wait_until="domcontentloaded")
        await page.evaluate(
            """({token, user}) => {
                localStorage.setItem('token', token);
                localStorage.setItem('userInfo', JSON.stringify(user));
            }""",
            {"token": token, "user": user},
        )
        await page.reload(wait_until="networkidle")
        await page.wait_for_timeout(1500)
        await page.locator("h2", has_text="评论").first.scroll_into_view_if_needed()
        await page.wait_for_timeout(1800)
        await page.screenshot(path="docs/screenshots/replies-light.png")

        print("console errors:", errors if errors else "NONE")
        await browser.close()


asyncio.run(main())
