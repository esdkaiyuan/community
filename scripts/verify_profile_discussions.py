# -*- coding: utf-8 -*-
"""个人中心（数据概览 + 我参与的讨论）截图验证"""
import json
import sys
import urllib.request

from playwright.sync_api import sync_playwright

BASE = "http://localhost:5000/api"
OUT = "docs/screenshots/profile-discussions-light.png"
TOKEN_KEY = "token"          # 与 frontend/src/utils/storage.js 保持一致
USER_KEY = "userInfo"


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
    # 登录测试账号（profile_tester 已有 2 条评论在项目 19）
    login = api("/users/login", {"email": "profile_tester@test.local", "password": "test123456"})
    token = login["data"]["token"]
    me = login["data"]["user"]

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

        page.goto("http://localhost:3001/profile", wait_until="networkidle")
        page.wait_for_timeout(1500)
        # 滚动到讨论列表本体，等 reveal 动画完成后截图
        card = page.locator("a.group").first
        card.scroll_into_view_if_needed()
        page.wait_for_timeout(1600)
        page.screenshot(path=OUT)
        browser.close()

    print("console errors:", len(errors))
    for e in errors[:5]:
        print(" -", e)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
