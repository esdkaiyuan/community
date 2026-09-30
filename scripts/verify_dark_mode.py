#!/usr/bin/env python3
"""深色模式逐页走查：令牌跟随 + 写死色回归 + 深浅对照。

背景（第 17 轮）：组件层曾有 3 处写死 hex 绕过令牌 ——
  CommentSection 点赞激活 text-[#FF3B30]、AppHeader 未读徽章 bg-[#FF3B30]、
  ToastHost success bg-[#34C759]/10 text-[#34C759]。
修复口径：点赞/徽章红收敛到 --c-clay（深色 #FF453A = iOS dark systemRed），
success 绿新增 --c-green（浅 #34C759 / 深 #30D158）。

断言全部「钉死到具体令牌」：读 getComputedStyle 的 rgb 值，与令牌期望值全等比较
——不是「看起来像深色」这种主观谓词。期望值来自 style.css 的令牌注释（唯一事实）。

跑法：C:/Users/28916/AppData/Local/Programs/Python/Python313/python.exe scripts/verify_dark_mode.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _verify_common import (  # noqa: E402
    FRONT,
    PASSWORD,
    assert_fails,
    check,
    cleanup_project,
    cleanup_users,
    comment,
    create_project,
    finish,
    inject_login,
    register,
    sql_one,
    wait_unread,
)

from playwright.sync_api import sync_playwright  # noqa: E402

TS = time.strftime("%m%d%H%M%S")
PIDS, UIDS = [], []

# ---------- 令牌期望值（源：frontend/src/style.css，唯一事实） ----------
# clay 浅 #D70015 / 深 #FF453A；green 浅 #34C759 / 深 #30D158；paper 深色 0 0 0
CLAY_LIGHT, CLAY_DARK = "rgb(215, 0, 21)", "rgb(255, 69, 58)"
GREEN_LIGHT, GREEN_DARK = "rgb(52, 199, 89)", "rgb(48, 209, 88)"
PAPER_DARK = "rgb(0, 0, 0)"

PWD = PASSWORD  # 表单登录必须用注册时的同一密码（此前猜错导致 toast 用例假红）
MY_CONSOLE = []  # 本脚本自己的 console 收集窗（逐页切片用）


def slice_console():
    got, MY_CONSOLE[:] = MY_CONSOLE[:], []
    return got


def css_color(page, selector):
    return page.locator(selector).first.evaluate("el => getComputedStyle(el).color")


def css_bg(page, selector):
    return page.locator(selector).first.evaluate("el => getComputedStyle(el).backgroundColor")


def no_overflow(page):
    return page.evaluate(
        "document.documentElement.scrollWidth - document.documentElement.clientWidth"
    ) <= 1


def watch(page):
    page.on("console", lambda m: MY_CONSOLE.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: MY_CONSOLE.append(str(e)))
    return page


def login_via_form(page, email):
    """登录页表单提交（弹 success toast 的真实路径）。登录页是邮箱+密码"""
    page.goto(f"{FRONT}/login", wait_until="networkidle")
    page.fill("input[type='email']", email)
    page.fill("input[type='password']", PWD)
    page.click("button[type='submit']")


def main():
    owner = register("darkown")  # register 内部固定拼 TS，prefix 不得自带（超长 400）
    guest = register("darkgst")
    UIDS.extend([owner["uid"], guest["uid"]])
    pid = create_project(owner["token"], f"深色走查临时项目{TS}", tags=["深色走查"])
    PIDS.append(pid)
    comment(guest["token"], pid, f"深色走查评论 {TS}")  # 触发 owner 未读通知
    got = wait_unread(owner["token"], 1)
    check("owner 未读数为 1（guest 评论触发）", got == 1)

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ================= A. 深色段 =================
        print("\n== A. 深色模式（prefers-color-scheme: dark）==")
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = watch(ctx.new_page())
        page.emulate_media(color_scheme="dark")

        # A1. 页面底色 = 深色 paper 令牌（纯黑）。背景挂在 body 上（style.css @apply bg-paper），
        #     html 本身无背景——探测点必须取 body，取 html 拿到 transparent 是假红
        page.goto("http://localhost:3001/", wait_until="networkidle")
        bg = page.evaluate("getComputedStyle(document.body).backgroundColor")
        check(f"深色首页 body 底色 == paper 深色令牌（{PAPER_DARK}）", bg == PAPER_DARK)

        # A2. 登录态逐页：console 零错误 + 无横向溢出
        inject_login(page, owner["token"], owner["user"])
        for path, label in [
            ("/", "首页"),
            ("/login", "登录页"),
            ("/register", "注册页"),
            (f"/project/{pid}", "项目详情"),
            ("/profile", "个人中心"),
            ("/notifications", "通知"),
            ("/security", "账号安全"),
            ("/no-such-page", "404 页"),
        ]:
            page.goto(f"http://localhost:3001{path}", wait_until="networkidle")
            page.wait_for_timeout(400)  # 等水合余波
            errs = slice_console()
            check(f"深色 {label} console 零错误", not errs)
            if errs:
                print("       console:", errs[:3])
            check(f"深色 {label} 无横向溢出", no_overflow(page))

        # A3. 未读徽章深色 == clay 深色令牌
        page.goto("http://localhost:3001/notifications", wait_until="networkidle")
        try:
            page.wait_for_selector("[data-test='unread-badge']", timeout=5000)
            badge_bg = css_bg(page, "[data-test='unread-badge']")
            check(f"深色未读徽章 == clay 深色令牌（{CLAY_DARK}）", badge_bg == CLAY_DARK)
        except Exception:
            check("深色未读徽章出现（owner 有未读）", False)

        # A4. 点赞激活态深色 == clay 深色令牌
        page.goto(f"http://localhost:3001/project/{pid}", wait_until="networkidle")
        like = page.locator("[data-test='comment-like']").first
        like.wait_for(state="visible", timeout=8000)
        like.click()
        page.wait_for_timeout(400)
        check("点赞后 aria-pressed=true", like.get_attribute("aria-pressed") == "true")
        check(
            f"深色点赞激活色 == clay 深色令牌（{CLAY_DARK}）",
            css_color(page, "[data-test='comment-like']") == CLAY_DARK,
        )

        # A5. toast success 深色 == green 深色令牌
        page.evaluate("() => { localStorage.removeItem('token'); localStorage.removeItem('userInfo') }")
        login_via_form(page, f"{owner['username']}@example.com")
        try:
            page.wait_for_selector("[data-test='toast-success']", timeout=5000)
            got = css_color(page, "[data-test='toast-success'] > span")
            if got != GREEN_DARK:
                print(f"       [诊断] 深色 toast 实际色值: {got}")
            check(f"深色 success 提示 == green 深色令牌（{GREEN_DARK}）", got == GREEN_DARK)
        except Exception:
            check("深色登录成功弹出 success 提示", False)
        ctx.close()

        # ================= B. 浅色对照段 =================
        print("\n== B. 浅色对照（令牌浅色值不变）==")
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = watch(ctx.new_page())
        page.emulate_media(color_scheme="light")
        inject_login(page, owner["token"], owner["user"])

        # B1. 浅色点赞激活 == clay 浅色令牌
        page.goto(f"http://localhost:3001/project/{pid}", wait_until="networkidle")
        like = page.locator("[data-test='comment-like']").first
        like.wait_for(state="visible", timeout=8000)
        # 先取消上一段的赞，回到未激活再点，保证断言的是「激活」色
        if like.get_attribute("aria-pressed") == "true":
            like.click()
            page.wait_for_timeout(300)
        like.click()
        page.wait_for_timeout(400)
        check(
            f"浅色点赞激活色 == clay 浅色令牌（{CLAY_LIGHT}）",
            css_color(page, "[data-test='comment-like']") == CLAY_LIGHT,
        )

        # B2. 浅色徽章 == clay 浅色令牌
        page.goto("http://localhost:3001/notifications", wait_until="networkidle")
        try:
            page.wait_for_selector("[data-test='unread-badge']", timeout=5000)
            check(
                f"浅色未读徽章 == clay 浅色令牌（{CLAY_LIGHT}）",
                css_bg(page, "[data-test='unread-badge']") == CLAY_LIGHT,
            )
        except Exception:
            check("浅色未读徽章出现", False)

        # B3. 浅色 toast success == green 浅色令牌
        page.evaluate("() => { localStorage.removeItem('token'); localStorage.removeItem('userInfo') }")
        login_via_form(page, f"{guest['username']}@example.com")
        try:
            page.wait_for_selector("[data-test='toast-success']", timeout=5000)
            got = css_color(page, "[data-test='toast-success'] > span")
            if got != GREEN_LIGHT:
                print(f"       [诊断] 浅色 toast 实际色值: {got}")
            check(f"浅色 success 提示 == green 浅色令牌（{GREEN_LIGHT}）", got == GREEN_LIGHT)
        except Exception:
            check("浅色登录成功弹出 success 提示", False)
        ctx.close()
        browser.close()

        # ---- 清理：项目级联评论，再删用户 ----
        cleanup_project(pid, UIDS)
        print("残留项目:", sql_one(f"SELECT COUNT(*) FROM projects WHERE id = {pid}"))
        print("残留用户:", sql_one(
            f"SELECT COUNT(*) FROM users WHERE id IN ({','.join(map(str, UIDS))})"
        ))

    finish()


if __name__ == "__main__":
    main()
