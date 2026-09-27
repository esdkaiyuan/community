# -*- coding: utf-8 -*-
"""项目收藏验证：详情页收藏按钮态 + 顶部玻璃条书签 + 个人中心「我的收藏」分区"""
import json
import sys
import urllib.request

from playwright.sync_api import sync_playwright

BASE = "http://localhost:5000/api"
OUT_DETAIL = "docs/screenshots/favorite-detail-light.png"
OUT_PROFILE = "docs/screenshots/favorite-profile-light.png"


def api(path, data=None, token=None, method=None):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(data).encode() if data else None,
        headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})},
        method=method or ("POST" if data is not None else "GET"),
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def main():
    login = api("/users/login", {"email": "fav_tester@test.local", "password": "test123456"})
    token, me = login["data"]["token"], login["data"]["user"]

    # 造数：收藏 19 与 18 两个项目（重复收藏返回 409，可忽略）
    for pid in (19, 18):
        try:
            api(f"/projects/{pid}/favorite", {}, token)
        except urllib.error.HTTPError:
            pass

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

        # 1) 详情页：滚动过封面让玻璃条浮现，操作卡显示"已收藏"
        page.goto("http://localhost:3001/project/19", wait_until="networkidle")
        page.wait_for_timeout(1500)
        page.mouse.wheel(0, 700)
        page.wait_for_timeout(1200)
        favorite_btn = page.get_by_role("button", name="已收藏")
        print("操作卡已收藏按钮:", favorite_btn.count() > 0)
        page.screenshot(path=OUT_DETAIL)

        # 2) 个人中心：概览条 + 我的收藏
        page.goto("http://localhost:3001/profile", wait_until="networkidle")
        page.wait_for_timeout(1800)
        heading = page.get_by_role("heading", name="我的收藏")
        heading.scroll_into_view_if_needed()
        page.wait_for_timeout(600)
        cards = page.locator("a[href^='/project/']")
        print("我的收藏卡片:", cards.count())
        if cards.count():
            cards.last.scroll_into_view_if_needed()
        page.wait_for_timeout(1600)
        page.screenshot(path=OUT_PROFILE)

        # 3) 交互：详情页取消收藏 → 按钮回到"收藏项目"
        page.goto("http://localhost:3001/project/18", wait_until="networkidle")
        page.wait_for_timeout(1300)
        page.get_by_role("button", name="已收藏").click()
        page.wait_for_timeout(1200)
        print("取消后按钮:", page.get_by_role("button", name="收藏项目").count() > 0)
        # 恢复收藏，便于个人中心截图数据一致
        page.get_by_role("button", name="收藏项目").click()
        page.wait_for_timeout(1000)

        browser.close()

    print("console errors:", len(errors))
    for e in errors[:5]:
        print(" -", e)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
