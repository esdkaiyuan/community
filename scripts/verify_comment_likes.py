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
    # 造数：注册临时用户，点赞已有的根评论（取第一条）
    reg = api("/users/register", {"username": "ui_like_demo", "email": "ui_like_demo@test.local", "password": "test123456"})
    token = reg["data"]["token"]
    user = reg["data"]["user"]
    root = api("/projects/19/comments")["data"]["comments"][0]
    api("/projects/19/comments/%d/like" % root["id"], token=token, method="POST")

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
        await page.screenshot(path="docs/screenshots/comment-likes-light.png")

        print("console errors:", errors if errors else "NONE")
        await browser.close()


asyncio.run(main())
