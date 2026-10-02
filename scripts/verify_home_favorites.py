# -*- coding: utf-8 -*-
"""广场「只看收藏」+ 卡片收藏徽标 验证

链路：
1) 注册临时用户 -> 收藏 1 个已有项目（库里仅 2 个项目，收藏 1 个即可验证筛选收窄）
2) API 断言：未登录无 favorited 字段；登录后标记正确；favorited=1 收窄集合；未登录时忽略该筛选
3) Playwright：注入登录态 -> 首页点「只看收藏」-> 卡片数收窄到 1 且带书签徽标 -> 深浅色截图
4) 清理：删除临时用户（级联删除其收藏）
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

from playwright.sync_api import sync_playwright

BASE = "http://localhost:5000/api"
MYSQL = r"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe"
from _db_config import DB_NAME, DB_PASS
DB = DB_NAME
OUT_LIGHT = "docs/screenshots/home-favorites-light.png"
OUT_DARK = "docs/screenshots/home-favorites-dark.png"
OUT_EMPTY = "docs/screenshots/home-favorites-empty.png"

TS = str(int(time.time()))[-6:]
USERNAME = f"homefav{TS}"
EMAIL = f"{USERNAME}@example.com"
PASSWORD = "test123456"

console_errors = []
assert_fails = []


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
        [MYSQL, "-u", "co_creation_esdk", DB, "-e", statement],
        check=True,
        capture_output=True,
        env={**os.environ, "MYSQL_PWD": DB_PASS},
    )


def check(label, cond):
    print(("  OK  " if cond else " FAIL ") + label)
    if not cond:
        assert_fails.append(label)


def main():
    reg = api("/users/register", {"username": USERNAME, "email": EMAIL, "password": PASSWORD})
    token, me = reg["data"]["token"], reg["data"]["user"]
    uid = me["id"]
    print(f"临时用户 id={uid} username={USERNAME}")

    try:
        all_ids = [p["id"] for p in api("/projects?pageSize=50")["data"]["projects"]]
        assert len(all_ids) >= 2, "库里项目不足 2 个，无法验证筛选收窄"
        fav_id, other_id = all_ids[0], all_ids[1]
        api(f"/projects/{fav_id}/favorite", {}, token)
        print(f"收藏 {fav_id}（未收藏 {other_id}）")

        # ---------- API 断言 ----------
        anon = api("/projects?pageSize=50")["data"]
        check("未登录列表不返回 favorited 字段", "favorited" not in anon["projects"][0])

        authed = api("/projects?pageSize=50", token=token)["data"]
        marks = {p["id"]: p.get("favorited") for p in authed["projects"]}
        check("收藏项标记 favorited=true", marks.get(fav_id) is True)
        check("未收藏项标记 favorited=false", marks.get(other_id) is False)

        only = api("/projects?favorited=1&pageSize=50", token=token)["data"]
        check(
            "favorited=1 收窄到仅收藏的项目",
            only["total"] == 1 and [p["id"] for p in only["projects"]] == [fav_id],
        )

        anon_only = api("/projects?favorited=1&pageSize=50")["data"]
        check("未登录时 favorited 被忽略（退化为全量）", anon_only["total"] == len(all_ids))

        # ---------- 前端交互 ----------
        with sync_playwright() as p:
            browser = p.chromium.launch()
            ctx = browser.new_context(viewport={"width": 1280, "height": 950}, device_scale_factor=2)
            page = ctx.new_page()
            page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: console_errors.append(str(e)))

            page.goto("http://localhost:3001/login", wait_until="networkidle")
            page.evaluate(
                "([t, u]) => { localStorage.setItem('token', t); localStorage.setItem('userInfo', JSON.stringify(u)) }",
                [token, me],
            )
            page.goto("http://localhost:3001/", wait_until="networkidle")
            page.wait_for_timeout(1600)

            cards = page.locator("a[href^='/project/']")
            check("默认列表展示全部项目", cards.count() == len(all_ids))

            pill = page.get_by_role("button", name="只看收藏")
            check("登录后出现「只看收藏」筛选", pill.count() == 1)
            pill.click()
            page.wait_for_timeout(1600)

            check("筛选后卡片数收窄到 1", cards.count() == 1)
            check("卡片带已收藏态按钮", page.locator("article button[aria-label='取消收藏']").count() == 1)
            check("URL 带上 favorited=1", "favorited=1" in page.url)

            page.screenshot(path=OUT_LIGHT)
            print("截图:", OUT_LIGHT)

            page.emulate_media(color_scheme="dark")
            page.wait_for_timeout(900)
            page.screenshot(path=OUT_DARK)
            print("截图:", OUT_DARK)

            # 再次点击回到全量列表
            page.emulate_media(color_scheme="light")
            page.get_by_role("button", name="只看收藏").click()
            page.wait_for_timeout(1600)
            check("取消筛选后恢复全量项目", cards.count() == len(all_ids))
            check("URL 不再带 favorited", "favorited" not in page.url)

            # ---------- 详情页收藏微动效 ----------
            page.goto(f"http://localhost:3001/project/{fav_id}", wait_until="networkidle")
            page.wait_for_timeout(1300)
            page.get_by_role("button", name="已收藏").click()  # 先取消，才能触发动效
            page.wait_for_timeout(1200)
            page.get_by_role("button", name="收藏项目").click()
            try:
                page.wait_for_selector(".fav-pop", timeout=2000)
                check("收藏成功播放 fav-pop 动效类", True)
                # Vue scoped 会给 keyframes 加 hash 后缀，这里只比对前缀
                anim = page.eval_on_selector(
                    ".fav-pop",
                    """el => {
                      const svg = el.querySelector('svg');
                      return {
                        halo: getComputedStyle(el).animationName,
                        icon: svg ? getComputedStyle(svg).animationName : ''
                      };
                    }""",
                )
                check("按钮播放光晕扩散动画", anim["halo"].startswith("fav-halo"))
                check("书签图标播放上挑回弹动画", anim["icon"].startswith("fav-icon-lift"))
            except Exception:  # noqa: BLE001
                check("收藏成功播放 fav-pop 动效类", False)

            # 动效结束后类应自动移除，避免常驻
            page.wait_for_timeout(900)
            check("动效结束后移除 fav-pop 类", page.locator(".fav-pop").count() == 0)

            browser.close()
    finally:
        # activity_logs 刻意不挂外键，级联收拾不到，必须显式清
        sql(f"DELETE FROM activity_logs WHERE user_id = {uid};")
        sql(f"DELETE FROM users WHERE id = {uid};")
        print("已清理临时用户:", uid)

    # ---------- 空状态：一个还没收藏过任何项目的用户 ----------
    empty = api("/users/register", {"username": f"homefav0{TS}", "email": f"homefav0{TS}@example.com", "password": PASSWORD})
    etok, eme, euid = empty["data"]["token"], empty["data"]["user"], empty["data"]["user"]["id"]
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 950}, device_scale_factor=2)
            page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: console_errors.append(str(e)))
            page.goto("http://localhost:3001/login", wait_until="networkidle")
            page.evaluate(
                "([t, u]) => { localStorage.setItem('token', t); localStorage.setItem('userInfo', JSON.stringify(u)) }",
                [etok, eme],
            )
            page.goto("http://localhost:3001/?favorited=1", wait_until="networkidle")
            page.wait_for_timeout(1400)
            check("无收藏时展示专属空状态", page.get_by_text("还没有收藏任何项目").count() == 1)
            check("空状态不展示任何项目卡片", page.locator("a[href^='/project/']").count() == 0)
            page.screenshot(path=OUT_EMPTY)
            print("截图:", OUT_EMPTY)
            browser.close()
    finally:
        # activity_logs 刻意不挂外键，级联收拾不到，必须显式清
        sql(f"DELETE FROM activity_logs WHERE user_id = {euid};")
        sql(f"DELETE FROM users WHERE id = {euid};")
        print("已清理空状态用户:", euid)

    print("assert failed:", len(assert_fails))
    for f in assert_fails:
        print(" -", f)
    print("console errors:", len(console_errors))
    for e in console_errors[:5]:
        print(" -", e)
    sys.exit(1 if (assert_fails or console_errors) else 0)


if __name__ == "__main__":
    main()
