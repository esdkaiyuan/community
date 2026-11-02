# -*- coding: utf-8 -*-
"""外观设置走查：明暗三态（跟随系统 / 浅色 / 深色）+ 四套强调色。

覆盖：
  A. 默认「跟随系统」：浅色启动、系统切深色后**不刷新即时跟随**、刷新仍跟随
  B. 手动覆盖：深色 / 浅色都能压过系统，且刷新后保持；切回「跟随系统」恢复自动
  C. 强调色：四套色值的浅色 / 深色两档都精确落到 --c-pine，text-pine 渲染色同步
  D. 语义色不被主题色污染：clay / green / cream / paper 保持各自令牌
  E. 持久化、重置默认、meta theme-color、非法存储值兜底
  F. 入口（页脚 + 账号菜单）与 375 宽无横向溢出、console 零错误

跑法：python scripts/verify_theme.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _verify_common import (  # noqa: E402
    FRONT,
    attach,
    check,
    cleanup_users,
    finish,
    inject_login,
    register,
)

from playwright.sync_api import sync_playwright  # noqa: E402

MODE_KEY = "community-theme-mode"
ACCENT_KEY = "community-theme-accent"

LIGHT_TOKENS = {
    "pine": "11 114 133",
    "azure": "10 91 181",
    "moss": "14 122 75",
    "iris": "107 63 184",
}
DARK_TOKENS = {
    "pine": "91 224 235",
    "azure": "108 182 255",
    "moss": "76 217 154",
    "iris": "196 166 255",
}

PAPER_LIGHT = "rgb(244, 241, 233)"
PAPER_DARK = "rgb(0, 0, 0)"
CREAM_LIGHT = "253 252 248"
CREAM_DARK = "18 20 25"
CLAY_LIGHT, CLAY_DARK = "215 0 21", "255 69 58"
GREEN_LIGHT, GREEN_DARK = "52 199 89", "48 209 88"


def token(page, name):
    return page.evaluate(f"getComputedStyle(document.documentElement).getPropertyValue('{name}').trim()")


def rgb(triplet):
    return "rgb({})".format(", ".join(triplet.split()))


def data(page, key):
    return page.evaluate(f"document.documentElement.dataset.{key}")


def body_bg(page):
    return page.evaluate("getComputedStyle(document.body).backgroundColor")


def stored(page, key):
    return page.evaluate(f"localStorage.getItem('{key}')")


def meta_theme(page):
    return page.evaluate("document.querySelector('meta[name=\\'theme-color\\']').content")


def wait_data(page, key, value, timeout=3000):
    """等 data-* 变成期望值；超时不抛异常，返回 False 交给 check 记 FAIL"""
    try:
        page.wait_for_function(
            f"document.documentElement.dataset.{key} === {value!r}", timeout=timeout
        )
        return True
    except Exception:  # noqa: BLE001
        return False


def wait_bg(page, expected, timeout=3000):
    try:
        page.wait_for_function(
            "e => getComputedStyle(document.body).backgroundColor === e", arg=expected, timeout=timeout
        )
        return True
    except Exception:  # noqa: BLE001
        return False


def no_overflow(page):
    return page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 1


def set_pref(page, mode=None, accent=None):
    """在已加载的同源页面里写偏好，然后由调用方刷新"""
    if mode is not None:
        page.evaluate(f"localStorage.setItem('{MODE_KEY}', '{mode}')")
    if accent is not None:
        page.evaluate(f"localStorage.setItem('{ACCENT_KEY}', '{accent}')")


def main():
    uids = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()

        # ================= A. 跟随系统（默认态） =================
        print("\n== A. 跟随系统（未做过任何手动选择）==")
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = attach(ctx.new_page())
        page.emulate_media(color_scheme="light")
        page.goto(f"{FRONT}/appearance", wait_until="networkidle")

        check("首次进入 data-theme == light", data(page, "theme") == "light")
        check("首次进入 data-accent == pine", data(page, "accent") == "pine")
        check(f"浅色 body 底色 == {PAPER_LIGHT}", body_bg(page) == PAPER_LIGHT)
        check("未写入 mode 存储（保持默认）", stored(page, MODE_KEY) is None)
        check("meta theme-color == #F4F1E9", meta_theme(page) == "#F4F1E9")
        check("三段明暗选项齐全", page.locator("button[data-test^='theme-mode-']").count() == 3)

        # 系统切深色：不刷新，页面即时跟随（verify 的关键差异点）
        page.emulate_media(color_scheme="dark")
        ok = wait_data(page, "theme", "dark")
        check("系统切深色后 data-theme 即时变 dark（未刷新）", ok)
        check(f"深色 body 底色 == {PAPER_DARK}", body_bg(page) == PAPER_DARK)
        check("深色 meta theme-color == #000000", meta_theme(page) == "#000000")

        # 刷新：仍是跟随系统（没有被当成手动深色写进存储）
        page.reload(wait_until="networkidle")
        check("刷新后仍 data-theme == dark", data(page, "theme") == "dark")
        check(f"刷新后深色 body 底色 == {PAPER_DARK}", body_bg(page) == PAPER_DARK)
        check("刷新后 mode 存储仍为空", stored(page, MODE_KEY) is None)

        # 系统切回浅色：同样即时跟随
        page.emulate_media(color_scheme="light")
        check("系统切浅色后 data-theme 即时变 light", wait_data(page, "theme", "light"))
        check(f"浅色 body 底色 == {PAPER_LIGHT}", body_bg(page) == PAPER_LIGHT)

        # 跟随系统必须在**任何页面**都常驻（不只是外观设置页）：回首页验证监听仍然生效
        page.goto(f"{FRONT}/", wait_until="networkidle")
        page.emulate_media(color_scheme="dark")
        check("首页（非外观页）也即时跟随系统", wait_bg(page, PAPER_DARK))
        page.emulate_media(color_scheme="light")
        check("首页系统切回浅色同样即时", wait_bg(page, PAPER_LIGHT))
        page.goto(f"{FRONT}/appearance", wait_until="networkidle")

        # ================= B. 手动覆盖 =================
        print("\n== B. 手动明暗覆盖与持久化 ==")
        page.click("[data-test='theme-mode-dark']")
        check("手动深色：data-theme == dark", data(page, "theme") == "dark")
        check("手动深色：存储 mode == dark", stored(page, MODE_KEY) == "dark")
        check(f"手动深色：body 底色 == {PAPER_DARK}", body_bg(page) == PAPER_DARK)

        # 系统是浅色，刷新后仍然深色 —— 手动选择压过系统
        page.reload(wait_until="networkidle")
        check("系统浅色 + 手动深色：刷新后仍 dark", data(page, "theme") == "dark")

        page.click("[data-test='theme-mode-light']")
        check("手动浅色：data-theme == light", data(page, "theme") == "light")
        check("手动浅色：存储 mode == light", stored(page, MODE_KEY) == "light")

        # 系统切成深色，刷新后仍是浅色
        page.emulate_media(color_scheme="dark")
        check("系统深色 + 手动浅色：不刷新仍 light", data(page, "theme") == "light")
        page.reload(wait_until="networkidle")
        check("系统深色 + 手动浅色：刷新后仍 light", data(page, "theme") == "light")
        check(f"系统深色 + 手动浅色：body 底色 == {PAPER_LIGHT}", body_bg(page) == PAPER_LIGHT)

        # 切回跟随系统：深色立即生效
        page.click("[data-test='theme-mode-system']")
        check("切回跟随系统：data-theme == dark", data(page, "theme") == "dark")
        check("切回跟随系统：存储 mode == system", stored(page, MODE_KEY) == "system")

        # ================= C. 四套强调色（浅色档） =================
        print("\n== C. 强调色：浅色档 ==")
        page.emulate_media(color_scheme="light")
        page.reload(wait_until="networkidle")
        for name, value in LIGHT_TOKENS.items():
            page.click(f"[data-test='accent-option'][data-accent='{name}']")
            check(f"浅色 {name}：--c-pine == {value}", token(page, "--c-pine") == value)
            check(f"浅色 {name}：data-accent == {name}", data(page, "accent") == name)
            check(
                f"浅色 {name}：.text-pine 渲染色同步",
                page.locator("[data-test='theme-preview'] a.text-pine").evaluate(
                    "el => getComputedStyle(el).color"
                ) == rgb(value),
            )
            check(f"浅色 {name}：选中态 aria-pressed", page.locator(
                f"[data-test='accent-option'][data-accent='{name}']"
            ).get_attribute("aria-pressed") == "true")

        # 持久化：刷新后 iris 仍在
        page.reload(wait_until="networkidle")
        check("强调色刷新后保持 iris", data(page, "accent") == "iris")
        check("强调色刷新后 --c-pine 仍为 iris", token(page, "--c-pine") == LIGHT_TOKENS["iris"])
        check("强调色存储 accent == iris", stored(page, ACCENT_KEY) == "iris")

        # ================= D. 语义色不被主题色污染 =================
        print("\n== D. 语义色 / 纸面令牌不随强调色变化 ==")
        check("浅色 + iris：--c-clay 不变", token(page, "--c-clay") == CLAY_LIGHT)
        check("浅色 + iris：--c-green 不变", token(page, "--c-green") == GREEN_LIGHT)
        check("浅色 + iris：--c-cream 不变", token(page, "--c-cream") == CREAM_LIGHT)
        check("浅色 + iris：--c-paper 不变", token(page, "--c-paper") == "244 241 233")

        # ================= C2. 四套强调色（深色档） =================
        print("\n== C2. 强调色：深色档 ==")
        page.click("[data-test='theme-mode-dark']")
        page.wait_for_timeout(150)
        for name, value in DARK_TOKENS.items():
            page.click(f"[data-test='accent-option'][data-accent='{name}']")
            check(f"深色 {name}：--c-pine == {value}", token(page, "--c-pine") == value)
            check(f"深色 {name}：data-theme 仍为 dark", data(page, "theme") == "dark")
        check("深色 + iris：--c-clay 不变", token(page, "--c-clay") == CLAY_DARK)
        check("深色 + iris：--c-green 不变", token(page, "--c-green") == GREEN_DARK)
        check("深色 + iris：--c-cream 不变", token(page, "--c-cream") == CREAM_DARK)
        check("深色 + iris：--c-paper 纯黑", token(page, "--c-paper") == "0 0 0")

        # 深色 + iris 刷新后两档都还在
        page.reload(wait_until="networkidle")
        check("深色 + iris 刷新：data-theme == dark", data(page, "theme") == "dark")
        check("深色 + iris 刷新：--c-pine 仍为深色 iris", token(page, "--c-pine") == DARK_TOKENS["iris"])

        # ================= E. 重置 / 非法值 / 入口 =================
        print("\n== E. 重置默认、非法存储值、入口 ==")
        page.click("[data-test='theme-reset']")
        check("重置：data-accent == pine", data(page, "accent") == "pine")
        check("重置：存储 accent == pine", stored(page, ACCENT_KEY) == "pine")
        check("重置：存储 mode == system", stored(page, MODE_KEY) == "system")
        # 此处系统外观为浅色（C 段切回 light 后未再改），所以重置后应解析为 light
        check("重置：跟随系统解析为 light", data(page, "theme") == "light")

        # 非法存储值：应兜底为 system + pine，而不是把坏值写到属性上
        set_pref(page, mode="neon", accent="pink")
        page.reload(wait_until="networkidle")
        check("非法 mode 兜底：data-theme 仍按系统解析", data(page, "theme") == "light")
        check("非法 accent 兜底：data-accent == pine", data(page, "accent") == "pine")
        check("非法 accent 兜底：--c-pine == 浅色 pine", token(page, "--c-pine") == LIGHT_TOKENS["pine"])

        # 页脚入口（游客可见）
        page.emulate_media(color_scheme="light")
        page.reload(wait_until="networkidle")
        check("游客页脚有外观设置入口", page.locator("[data-test='appearance-footer']").count() == 1)
        page.click("[data-test='appearance-footer']")
        page.wait_for_timeout(300)
        check("页脚入口跳到 /appearance", page.url.endswith("/appearance"))

        # 移动端 375：明暗 + 主题色都不许横向溢出
        print("\n== E2. 移动端 375 ==")
        page.set_viewport_size({"width": 375, "height": 812})
        for mode_test, label in [
            ("theme-mode-light", "浅色"),
            ("theme-mode-dark", "深色"),
            ("theme-mode-system", "跟随系统"),
        ]:
            page.click(f"[data-test='{mode_test}']")
            page.wait_for_timeout(120)
            check(f"375 宽 {label} 无横向溢出", no_overflow(page))
        for name in LIGHT_TOKENS:
            page.click(f"[data-test='accent-option'][data-accent='{name}']")
            check(f"375 宽 {name} 无横向溢出", no_overflow(page))
        check("375 宽四个主题色选项都在一屏内", page.locator("[data-test='accent-option']").count() == 4)

        # 账号菜单入口：临时账号注入登录后点开菜单
        print("\n== F. 账号菜单入口 ==")
        account = register("theme")
        uids.append(account["uid"])
        inject_login(page, account["token"], account["user"])
        page.goto(f"{FRONT}/", wait_until="networkidle")
        page.click("button[aria-label='账号菜单']")
        page.wait_for_selector("[data-test='appearance-entry']", timeout=3000)
        check("账号菜单有外观入口", page.locator("[data-test='appearance-entry']").count() == 1)
        page.click("[data-test='appearance-entry']")
        page.wait_for_timeout(300)
        check("账号菜单入口跳到 /appearance", page.url.endswith("/appearance"))
        check("账号菜单点完收起", page.locator("[data-test='appearance-entry']").count() == 0)

        # 收尾：回到桌面宽，清掉本脚本写入的偏好，避免污染后续手动浏览
        page.set_viewport_size({"width": 1280, "height": 900})
        page.evaluate(f"localStorage.removeItem('{MODE_KEY}'); localStorage.removeItem('{ACCENT_KEY}')")
        page.reload(wait_until="networkidle")
        check("清除偏好后回到默认跟随系统（浅色）", data(page, "theme") == "light")

        browser.close()

    try:
        cleanup_users(uids)
    except Exception as err:  # noqa: BLE001
        print("cleanup failed:", err)

    finish()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        import traceback

        traceback.print_exc()
        print("CRASH:", exc)
        finish()
        sys.exit(1)
