# -*- coding: utf-8 -*-
"""项目卡「就地收藏」验证

覆盖：
1) 桌面端按钮默认透明、卡片悬停后浮现；触屏视口常显
2) 点击收藏不跳转详情页，图标转实心、aria-pressed 翻转、播放 fav-pop 动效
3) 服务端状态同步（GET /projects 带 token 复核 favorited）
4) 「只看收藏」里就地取消收藏 -> 卡片即时移出 -> 落到空状态
5) 个人中心「我的收藏」里就地取消收藏 -> 卡片即时移出、分区计数回落
6) 未登录点击 -> 引导到登录页
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

from playwright.sync_api import sync_playwright

BASE = "http://localhost:5000/api"
FRONT = "http://localhost:3001"
MYSQL = r"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe"
from _db_config import DB_NAME, DB_PASS, DB_USER  # 凭据只从环境变量 / backend/.env 读取

TS = str(int(time.time()))[-6:]
USERNAME = f"favcard{TS}"
EMAIL = f"{USERNAME}@example.com"
PASSWORD = "test123456"

assert_fails = []
console_errors = []


def api(path, data=None, token=None, method=None):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(data).encode() if data is not None else None,
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
        method=method or ("POST" if data is not None else "GET"),
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def sql(statement):
    subprocess.run(
        [MYSQL, "-u", DB_USER, DB_NAME, "-e", statement],
        check=True,
        capture_output=True,
        env={**os.environ, "MYSQL_PWD": DB_PASS},
    )


def check(label, cond):
    print(("  OK  " if cond else " FAIL ") + label)
    if not cond:
        assert_fails.append(label)


def attach(page):
    page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: console_errors.append(str(e)))


def inject_login(page, token, user):
    page.goto(f"{FRONT}/login", wait_until="networkidle")
    page.evaluate(
        "([t, u]) => { localStorage.setItem('token', t); localStorage.setItem('userInfo', JSON.stringify(u)) }",
        [token, user],
    )


def main():
    reg = api("/users/register", {"username": USERNAME, "email": EMAIL, "password": PASSWORD})
    token, me, uid = reg["data"]["token"], reg["data"]["user"], reg["data"]["user"]["id"]
    print(f"临时用户 id={uid}")

    all_ids = [p["id"] for p in api("/projects?pageSize=50")["data"]["projects"]]
    assert len(all_ids) >= 2, "库里项目不足 2 个，无法验证"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()

            # ============ A. 桌面端：悬停浮现 + 就地收藏 ============
            page = browser.new_page(viewport={"width": 1280, "height": 950}, device_scale_factor=2)
            attach(page)
            inject_login(page, token, me)
            page.goto(f"{FRONT}/", wait_until="networkidle")
            page.wait_for_timeout(1600)

            card = page.locator("article").first
            btn = card.locator("button").first
            # 断言基准是「页面上真实渲染的卡片数」，不是库里项目总数 —— 首页每页只渲染
            # 12 张卡，拿库里全部项目数去比会永远少 6 个（首页分页使然，与按钮无关）。
            # 另外已收藏的卡片 aria-label 会变成「取消收藏」，所以按 data-test 计数。
            card_count = page.locator("article").count()
            fav_btn_count = page.locator("article button[data-test='card-fav']").count()
            check(
                f"每张卡片都有收藏按钮（卡片 {card_count} / 按钮 {fav_btn_count}）",
                card_count > 0 and fav_btn_count == card_count,
            )

            opacity_idle = btn.evaluate("el => getComputedStyle(el).opacity")
            card.hover()
            page.wait_for_timeout(350)
            opacity_hover = btn.evaluate("el => getComputedStyle(el).opacity")
            check(f"桌面默认隐藏（opacity={opacity_idle}）", opacity_idle == "0")
            check(f"悬停后浮现（opacity={opacity_hover}）", opacity_hover == "1")

            # 收藏不跳转（fav-pop 只活 560ms，必须等它出现而不是睡固定时长）
            url_before = page.url
            btn.click()
            pulse_ok = True
            try:
                page.wait_for_selector("article .fav-pop", timeout=2500)
            except Exception:  # noqa: BLE001
                pulse_ok = False
            check("播放 fav-pop 动效", pulse_ok)
            check("点收藏不跳转详情页", page.url == url_before and url_before.rstrip("/") == FRONT.rstrip("/"))

            check("按钮翻转为取消收藏", card.locator("button[aria-label='取消收藏']").count() == 1)
            check("aria-pressed 为 true", card.locator("button[aria-pressed='true']").count() == 1)
            check(
                "书签图标转实心",
                card.locator("button svg").first.evaluate("el => el.getAttribute('fill')") == "currentColor",
            )
            page.screenshot(path="docs/screenshots/card-favorite-hover.png")

            # 服务端复核
            fav_id = all_ids[0]
            marks = {p["id"]: p.get("favorited") for p in api("/projects?pageSize=50", token=token)["data"]["projects"]}
            check("服务端已记录收藏", marks.get(fav_id) is True)

            # ============ B. 只看收藏里就地取消 -> 移出列表 ============
            page.goto(f"{FRONT}/?favorited=1", wait_until="networkidle")
            page.wait_for_timeout(1600)
            check("只看收藏里 1 张卡", page.locator("article").count() == 1)
            page.locator("article button[aria-label='取消收藏']").first.click()
            page.wait_for_timeout(1200)
            check("取消后卡片即时移出", page.locator("article").count() == 0)
            check("落到收藏空状态", page.get_by_text("还没有收藏任何项目").count() == 1)
            check("URL 仍停在只看收藏", "favorited=1" in page.url)
            page.screenshot(path="docs/screenshots/card-favorite-empty-after-remove.png")

            # 复原一个收藏，供个人中心验证
            api(f"/projects/{fav_id}/favorite", {}, token)

            # ============ C. 个人中心「我的收藏」就地取消 ============
            page.goto(f"{FRONT}/profile", wait_until="networkidle")
            page.wait_for_timeout(1800)
            heading = page.get_by_role("heading", name="我的收藏")
            heading.scroll_into_view_if_needed()
            page.wait_for_timeout(900)
            check("个人中心收藏区 1 张卡", page.locator("article").count() == 1)
            check("分区标题显示（1）", "（1）" in heading.inner_text())
            page.locator("article button[aria-label='取消收藏']").first.click()
            page.wait_for_timeout(1200)
            check("取消后卡片即时移出", page.locator("article").count() == 0)
            check("分区标题回落（0）", "（0）" in heading.inner_text())
            page.screenshot(path="docs/screenshots/card-favorite-profile-after-remove.png")
            page.close()

            # ============ D. 触屏视口：按钮常显 ============
            mobile = browser.new_page(viewport={"width": 414, "height": 896}, device_scale_factor=2)
            attach(mobile)
            inject_login(mobile, token, me)
            mobile.goto(f"{FRONT}/", wait_until="networkidle")
            mobile.wait_for_timeout(1600)
            m_btn = mobile.locator("article button").first
            check("触屏视口按钮常显", m_btn.evaluate("el => getComputedStyle(el).opacity") == "1")
            mobile.locator("article").first.scroll_into_view_if_needed()
            mobile.wait_for_timeout(1200)
            mobile.screenshot(path="docs/screenshots/card-favorite-mobile.png")
            mobile.close()

            # ============ E. 未登录点击 -> 引导登录 ============
            guest = browser.new_page(viewport={"width": 1280, "height": 950})
            attach(guest)
            guest.goto(f"{FRONT}/", wait_until="networkidle")
            guest.wait_for_timeout(1500)
            guest.locator("article").first.hover()
            guest.wait_for_timeout(300)
            guest.locator("article button").first.click()
            guest.wait_for_timeout(900)
            check("未登录点击跳转登录页", "/login" in guest.url)
            guest.close()

            browser.close()
    finally:
        # activity_logs 刻意不挂外键，级联收拾不到，必须显式清（否则每跑一轮留一批日志垃圾）
        sql(f"DELETE FROM activity_logs WHERE user_id = {uid};")
        sql(f"DELETE FROM users WHERE id = {uid};")
        print("已清理临时用户:", uid)

    print("assert failed:", len(assert_fails))
    for f in assert_fails:
        print(" -", f)
    print("console errors:", len(console_errors))
    for e in console_errors[:5]:
        print(" -", e)
    sys.exit(1 if (assert_fails or console_errors) else 0)


if __name__ == "__main__":
    main()
