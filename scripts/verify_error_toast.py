# -*- coding: utf-8 -*-
"""错误提示（toast）重设计 —— 端到端验证

在**仓库根目录**执行：
    "C:\\Users\\28916\\AppData\\Local\\Programs\\Python\\Python313\\python.exe" scripts/verify_error_toast.py

背景：旧提示的 `h-4.5 w-4.5` 不是合法 Tailwind 尺寸类（默认 spacing 只有 0.5/1.5/2.5/3.5），
SVG 因此失去尺寸约束被撑成巨型红叉，文字挤成竖排，整块压在导航栏上——本轮重做布局与分工。

覆盖：
A. 几何与防复发：右上角、不遮 sticky 导航栏、卡片不超视口、图标 ≤ 24px
B. 文案分工：4xx 原样展示 / 5xx 与断网用人话 / 登录页密码错误改成内联红字不弹全局提示 /
   带过期 token 的并发 401 只弹一张
C. 交互：✕ 关闭、悬停暂停倒计时、同文案去重、长文案换行不竖排、success/info 各自渲染
"""
import json

from playwright.sync_api import sync_playwright

from _verify_common import (
    FRONT,
    PASSWORD,
    attach,
    check,
    cleanup_users,
    console_errors,
    finish,
    register,
)

UIDS = []

TOAST = "[data-test^='toast-']"


def main():
    user = register("tst")
    UIDS.append(user["uid"])
    email = f"{user['username']}@example.com"
    print("临时用户:", user["uid"], email)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = attach(browser.new_page(viewport={"width": 1360, "height": 800}, device_scale_factor=2))

        # ---------- A. 几何与防复发 ----------
        page.goto(f"{FRONT}/register", wait_until="networkidle")
        page.fill("#username", "提示验证")
        page.fill("#email", email)
        page.fill("#password", PASSWORD)
        page.fill("#confirm", PASSWORD)
        page.click("button[type=submit]")
        page.wait_for_selector("[data-test='toast-error']", timeout=6000)
        page.wait_for_timeout(500)

        box = page.locator("[data-test='toast-error']").first.bounding_box()
        nav = page.locator("header").first.bounding_box()
        icon = page.locator("[data-test='toast-error'] svg").first.bounding_box()

        check("4xx 业务文案原样展示", "已被注册" in page.locator("[data-test='toast-error']").first.inner_text())
        check("提示落在右上角（不居中占满顶部）", box["x"] > 1360 / 2)
        check(f"提示不遮导航栏（toast.top={box['y']:.0f} >= nav.bottom={nav['y'] + nav['height']:.0f}）", box["y"] >= nav["y"] + nav["height"])
        check("卡片不超出视口右侧", box["x"] + box["width"] <= 1360)
        check(f"图标尺寸正常（{icon['width']:.0f}px，防 h-4.5 非法类复发）", icon["width"] <= 24 and icon["height"] <= 24)
        check("单行文案时卡片高度克制（< 80px）", box["height"] < 80)

        # 同文案去重：再点一次提交，仍然只有一张卡
        page.click("button[type=submit]")
        page.wait_for_timeout(1200)
        check("同类型同文案不叠加第二张", page.locator(TOAST).count() == 1)

        # 悬停暂停倒计时（error 默认 4.5s，hover 期间不该消失）
        page.locator(TOAST).first.hover()
        page.wait_for_timeout(5600)
        check("悬停期间倒计时暂停（超过 4.5s 仍在）", page.locator(TOAST).count() == 1)
        page.mouse.move(20, 400)
        page.wait_for_selector(TOAST, state="detached", timeout=6000)
        check("移开鼠标后走完剩余时间并自动消失", page.locator(TOAST).count() == 0)

        # ✕ 主动关闭
        page.click("button[type=submit]")
        page.wait_for_selector("[data-test='toast-error']", timeout=6000)
        page.locator("[aria-label='关闭提示']").first.click()
        page.wait_for_selector("[data-test='toast-error']", state="detached", timeout=3000)
        check("✕ 可立即关闭提示", page.locator(TOAST).count() == 0)

        # ---------- B. 文案分工：5xx 与断网 ----------
        page.route(
            "**/api/users/register",
            lambda r: r.fulfill(
                status=500,
                content_type="application/json",
                body=json.dumps({"code": 500, "message": "Internal Server Error"}),
            ),
        )
        page.click("button[type=submit]")
        page.wait_for_selector("[data-test='toast-error']", timeout=6000)
        text = page.locator("[data-test='toast-error']").first.inner_text()
        check("5xx 换成用户能懂的文案", "服务暂时不可用" in text)
        check("5xx 不把后端原始 message 甩给用户", "Internal Server Error" not in text)
        page.unroute("**/api/users/register")

        # 关闭后再测断网，避免同文案去重干扰
        page.locator("[aria-label='关闭提示']").first.click()
        page.wait_for_selector("[data-test='toast-error']", state="detached", timeout=3000)

        page.route("**/api/users/register", lambda r: r.abort())
        page.click("button[type=submit]")
        page.wait_for_selector("[data-test='toast-error']", timeout=6000)
        text = page.locator("[data-test='toast-error']").first.inner_text()
        check("断网给出「检查网络」而不是「服务器错误」", "网络连接失败" in text)
        page.unroute("**/api/users/register")

        # ---------- B2. 长文案：换行而不是竖排 ----------
        long_msg = (
            "这个邮箱已经被注册过了，如果你确定这就是你的账号，可以直接去登录；"
            "如果忘记密码，请先用另一个邮箱注册，或联系共创社区的管理员帮你找回。"
        )
        page.route(
            "**/api/users/register",
            lambda r: r.fulfill(
                status=400,
                content_type="application/json",
                body=json.dumps({"code": 400, "message": long_msg}, ensure_ascii=False).encode("utf-8"),
            ),
        )
        page.click("button[type=submit]")
        page.wait_for_selector("[data-test='toast-error']", timeout=6000)
        page.wait_for_timeout(400)
        lbox = page.locator("[data-test='toast-error']").first.bounding_box()
        check(f"长文案换行而不是竖排（宽 {lbox['width']:.0f} 高 {lbox['height']:.0f}）", lbox["width"] > lbox["height"])
        check("长文案仍不超出视口", lbox["x"] + lbox["width"] <= 1360)
        page.unroute("**/api/users/register")
        page.locator("[aria-label='关闭提示']").first.click()
        page.wait_for_timeout(500)

        # ---------- B3. 登录页密码错误：内联红字，不弹全局提示 ----------
        page.goto(f"{FRONT}/login", wait_until="networkidle")
        page.fill("#email", email)
        page.fill("#password", "wrong-password-123")
        page.click("button[type=submit]")
        page.wait_for_timeout(1500)
        check("登录页密码错误不弹全局提示", page.locator(TOAST).count() == 0)
        check("登录页把错误就地显示在密码框下", "邮箱或密码错误" in page.locator(".form-error").first.inner_text())

        # ---------- B4. 过期 token：并发 401 只弹一张 ----------
        page.evaluate("() => localStorage.setItem('token', 'eyJhbGciOiJIUzI1NiJ9.fake.token')")
        page.goto(f"{FRONT}/profile", wait_until="networkidle")
        page.wait_for_selector("[data-test='toast-error']", timeout=6000)
        page.wait_for_timeout(1500)
        check("登录态失效给出明确提示", "登录已过期" in page.locator("[data-test='toast-error']").first.inner_text())
        check("并发多个 401 只合成一张提示（不刷屏）", page.locator(TOAST).count() == 1)
        check("登录态失效后跳回登录页", page.url.endswith("/login") or "/login?" in page.url)

        # ---------- C. success / info 两种类型 ----------
        page.wait_for_timeout(4600)  # 等上一条自动消失
        page.goto(f"{FRONT}/login", wait_until="networkidle")
        page.fill("#email", email)
        page.fill("#password", PASSWORD)
        page.click("button[type=submit]")
        page.wait_for_selector("[data-test='toast-success']", timeout=6000)
        check("成功提示走 success 样式", "欢迎回来" in page.locator("[data-test='toast-success']").first.inner_text())

        # 截图：走真实发布表单，把 POST 拦成 400（浅色 / 深色各一张）
        page.goto(f"{FRONT}/publish", wait_until="networkidle")
        page.wait_for_timeout(1300)
        page.fill("#title", "提示样式实测项目")
        page.fill("#description", "这是一段用于验证提示样式的临时描述，长度足够通过前端校验。")
        page.locator("[data-test='category-option']").first.click()

        def reject_create(route):
            if route.request.method == "POST":
                route.fulfill(
                    status=400,
                    content_type="application/json",
                    body=json.dumps({"code": 400, "message": "请选择项目分类"}, ensure_ascii=False).encode("utf-8"),
                )
            else:
                route.continue_()

        page.route("**/api/projects", reject_create)
        page.locator("[data-test='submit-project']").click()
        page.wait_for_selector("[data-test='toast-error']", timeout=6000)
        page.wait_for_timeout(600)
        page.screenshot(path="docs/screenshots/error-toast-light.png")
        page.emulate_media(color_scheme="dark")
        page.wait_for_timeout(700)
        page.screenshot(path="docs/screenshots/error-toast-dark.png")
        page.unroute("**/api/projects")

        browser.close()


if __name__ == "__main__":
    try:
        main()
    finally:
        cleanup_users(UIDS)
        print("已清理临时用户")
        # 本脚本全程在故意制造 4xx / 5xx / 断网，浏览器会为每个失败请求自动记一条
        # 「Failed to load resource」——那是浏览器日志而不是应用错误（JS 报错不带这个前缀），
        # 统一剔除，否则「零 console 错误」永远过不了
        console_errors[:] = [e for e in console_errors if not e.startswith("Failed to load resource")]
    finish()
