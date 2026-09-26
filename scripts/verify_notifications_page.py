# -*- coding: utf-8 -*-
"""独立通知页验证：全部/未读 列表渲染 + 「查看全部通知」入口 + console 错误"""
import json
import sys
import urllib.request

from playwright.sync_api import sync_playwright

BASE = "http://localhost:5000/api"
OUT = "docs/screenshots/notifications-page-light.png"
OUT_UNREAD = "docs/screenshots/notifications-unread-light.png"


def api(path, data=None, token=None):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(data).encode() if data else None,
        headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})},
        method="POST" if data is not None else "GET",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def main():
    login = api("/users/login", {"email": "nf_author@test.local", "password": "test123456"})
    token, me = login["data"]["token"], login["data"]["user"]

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        errors = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))

        page.goto("http://localhost:3001/login", wait_until="networkidle")
        page.evaluate(
            "([t, u]) => { localStorage.setItem('token', t); localStorage.setItem('userInfo', JSON.stringify(u)) }",
            [token, me],
        )

        # 1) 全部通知页
        page.goto("http://localhost:3001/notifications", wait_until="networkidle")
        page.wait_for_timeout(1800)
        rows = page.locator(".card > button").count()
        heading = page.locator("h1").inner_text()
        print("全部视图 | 标题:", heading, "| 行数:", rows)
        page.screenshot(path=OUT)

        # 2) 未读筛选（分段控件第 2 项）
        page.get_by_role("button", name="未读", exact=True).click()
        page.wait_for_timeout(1500)
        unread_rows = page.locator(".card > button").count()
        print("未读视图 | 行数:", unread_rows, "| url:", page.url)
        page.screenshot(path=OUT_UNREAD)

        # 3) 交互：未读视图点击第一条 → 标为已读 + 跳转项目评论区，返回后该条应移出列表
        badge_before = page.locator("header span.rounded-full.bg-\\[\\#FF3B30\\]").inner_text()
        page.locator(".card > button").first.click()
        page.wait_for_timeout(1500)
        print("点击后跳转:", page.url, "| 跳转前徽标:", badge_before)
        page.goto("http://localhost:3001/notifications?filter=unread", wait_until="networkidle")
        page.wait_for_timeout(1600)
        rows_after = page.locator(".card > button").count()
        badge_after = page.locator("header span.rounded-full.bg-\\[\\#FF3B30\\]").inner_text()
        print("未读视图剩余行数:", rows_after, "| 跳转后徽标:", badge_after)

        # 4) 头部铃铛面板「查看全部通知」入口
        page.locator('button[title="通知"]').click()
        page.wait_for_timeout(800)
        footer = page.locator("a", has_text="查看全部通知")
        print("面板入口可见:", footer.count() > 0)
        page.screenshot(path="docs/screenshots/notifications-panel-footer-light.png")

        browser.close()

    print("console errors:", len(errors))
    for e in errors[:5]:
        print(" -", e)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
