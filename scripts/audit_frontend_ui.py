# -*- coding: utf-8 -*-
"""全站前端巡检 —— 路由 × 视口 × 主题 的横向体检

用户诉求：「检查整个平台的所有前端显示组件与当初设计时的预期是否有区别或 bug」。
这不是单一功能的端到端验证，而是一次**横向巡检**：把每个路由在
桌面 / 移动、浅色 / 深色下都走一遍，采集可自动判定的问题。

对的是 `docs/PROJECT_SUMMARY.md` 与 `README.md` 里写下的原始设计预期，
以及 `frontend/src/style.css` + `tailwind.config.js` 里的设计令牌体系。

覆盖：
A. 访客路由巡检：console 错误 / 横向溢出 / 文档标题 / 未登录访问受限页的跳转
B. 登录态路由巡检：同样四项 + 通知面板、个人中心、编辑页
C. 响应式：1440 / 834 / 390 三档宽度下均不得横向溢出
D. 主题：深色下不得出现浅色主题的硬编码底色（设计令牌漂移）
E. 结构：交互元素非法嵌套、图标尺寸、图片 alt、卡片封面配色一致性
F. 窄屏导航栏：用户名收起、铃铛与用户菜单在窄屏的落点与溢出

执行（**仓库根目录**）：
    "C:\\Users\\28916\\AppData\\Local\\Programs\\Python\\Python313\\python.exe" scripts/audit_frontend_ui.py
"""
from playwright.sync_api import sync_playwright

from _verify_common import (
    FRONT,
    attach,
    check,
    cleanup_project,
    cleanup_users,
    comment,
    console_errors,
    create_project,
    finish,
    inject_login,
    register,
)

UIDS = []
PIDS = []
SHOTS = "docs/screenshots"

# 故意访问不存在的资源时，浏览器会自行记一条 "Failed to load resource ... 404"，
# 那是网络日志而非 JS 报错，按预期剔除（见技能文档「零 console 错误」一节）
EXPECTED_404_HINTS = ("404", "Failed to load resource")

# 读出悬停实测底色，并据此算出「若它真的来自 --c-clay 令牌，应该是什么颜色」。
# 比「是不是深色」这种模糊判断强：它在浅色与深色下都成立，且能钉死到具体令牌。
HOVER_VS_TOKEN = r"""
() => {
  const el = document.querySelector("[data-test='comment-like']")
  const bg = getComputedStyle(el).backgroundColor
  const tok = getComputedStyle(document.documentElement).getPropertyValue('--c-clay').trim()
  const [r, g, b] = tok.split(/\s+/).map(Number)
  return { bg, expect: `rgba(${r}, ${g}, ${b}, 0.1)`, tok }
}
"""

WIDTHS = [(1440, 900, "desktop"), (834, 1112, "tablet"), (390, 844, "mobile"), (360, 780, "small"), (320, 720, "tiny")]


def overflow(page):
    return page.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")


def take(page, path, label, expect_404=False, shot=None, theme=None):
    """访问一条路由，采集 console 错误与横向溢出；返回 (错误列表, 溢出px)"""
    if theme:
        page.emulate_media(color_scheme=theme)
    mark = len(console_errors)
    page.goto(FRONT + path, wait_until="networkidle")
    page.wait_for_timeout(450)

    errs = list(console_errors[mark:])
    del console_errors[mark:]
    if expect_404:
        errs = [e for e in errs if not any(h in e for h in EXPECTED_404_HINTS)]
    console_errors.extend(errs)

    over = overflow(page)
    check(f"{label} 无 console 错误", not errs)
    check(f"{label} 无横向溢出（多出 {over}px）", over <= 1)
    if shot:
        page.screenshot(path=f"{SHOTS}/{shot}")

    return errs


def main():
    owner = register("aud")
    UIDS.append(owner["uid"])
    pid = create_project(owner["token"], f"巡检临时项目-{owner['uid']}", tags=["巡检", "端到端"])
    PIDS.append(pid)
    comment(owner["token"], pid, "巡检用评论：用来验证评论区的悬停与深色表现。")
    print(f"临时用户={owner['uid']}  临时项目={pid}")

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ================= A. 访客路由 =================
        print("\n== A. 访客路由巡检 ==")
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = attach(ctx.new_page())

        for path, label, exp404, shot in [
            ("/", "首页", False, "audit-home-light.png"),
            ("/login", "登录页", False, None),
            ("/register", "注册页", False, None),
            (f"/project/{pid}", "项目详情", False, "audit-detail-light.png"),
            ("/project/99999999", "不存在的项目", True, None),
            (f"/user/{owner['uid']}", "共创者主页", False, "audit-user-light.png"),
            ("/user/99999999", "不存在的用户", True, None),
            ("/no-such-page", "404 页", False, None),
        ]:
            take(page, path, label, expect_404=exp404, shot=shot)

        # 未登录访问受限页 -> 跳登录并带 redirect
        for path, label in [
            ("/profile", "个人中心"),
            ("/publish", "发布项目"),
            ("/notifications", "通知"),
            (f"/project/{pid}/edit", "编辑项目"),
        ]:
            take(page, path, f"未登录访问{label}", shot=None)
            check(
                f"未登录访问{label}跳登录页（{page.url.split('/', 3)[-1]}）",
                "/login" in page.url,
            )
        ctx.close()

        # ================= B. 登录态路由 =================
        print("\n== B. 登录态路由巡检 ==")
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = attach(ctx.new_page())
        inject_login(page, owner["token"], owner["user"])

        for path, label, exp404, shot in [
            ("/", "首页（登录态）", False, None),
            ("/profile", "个人中心", False, "audit-profile-light.png"),
            ("/notifications", "通知页", False, "audit-notifications-light.png"),
            ("/publish", "发布页", False, None),
            (f"/project/{pid}/edit", "编辑页", False, None),
            (f"/user/{owner['uid']}", "自己看自己的主页", False, None),
            (f"/project/{pid}", "详情页（登录态）", False, None),
        ]:
            take(page, path, label, expect_404=exp404, shot=shot)

        # ================= E. 结构与令牌（登录态，个人中心有自己的项目） =================
        print("\n== E. 结构与设计令牌 ==")
        page.goto(f"{FRONT}/profile", wait_until="networkidle")
        page.wait_for_timeout(600)

        # E1. 交互元素非法嵌套：编辑入口不得落在收藏按钮内部
        edit = page.locator("[data-test='card-edit']").first
        nested = edit.evaluate("e => !!e.closest('button')")
        check("「编辑项目」不是嵌在收藏按钮里的（非法嵌套已修）", not nested)

        # E2. 功能后果：点编辑只进编辑页，不顺带触发收藏请求
        fav_hits = []
        page.on("request", lambda r: fav_hits.append(r.url) if "/favorite" in r.url else None)
        edit.click()
        page.wait_for_url("**/edit", timeout=6000)
        page.wait_for_timeout(500)
        check("点「编辑项目」进入编辑页", "/edit" in page.url)
        check(f"点「编辑项目」不会顺带触发收藏（收藏请求 {len(fav_hits)} 次）", not fav_hits)

        # E3. 卡片封面占位配色与详情页一致（防两处色板各改一半）
        page.goto(f"{FRONT}/", wait_until="networkidle")
        page.wait_for_timeout(500)
        card_bg = page.evaluate(
            """() => {
                const link = document.querySelector(`[data-test='card-link'][href='/project/%d']`)
                    || [...document.querySelectorAll(`[data-test='card-link']`)].find(a => a.getAttribute('href') === '/project/%d')
                if (!link) return null
                const el = link.parentElement.querySelector('div[style*="linear-gradient"]')
                return el ? el.style.backgroundImage : null
            }""" % (pid, pid)
        )
        page.goto(f"{FRONT}/project/{pid}", wait_until="networkidle")
        page.wait_for_timeout(400)
        detail_bg = page.evaluate(
            """() => {
                const el = document.querySelector('div[style*="linear-gradient"]')
                return el ? el.style.backgroundImage : null
            }"""
        )
        check("卡片占位配色与详情页一致（同 id 同色板）", card_bg and card_bg == detail_bg)

        # E4. 图标尺寸不得失控（h-4.5 那类非法类会让 SVG 失去约束被撑爆）
        big = page.evaluate(
            """() => [...document.querySelectorAll('svg')]
                .filter(s => s.getBoundingClientRect().width > 48)
                .map(s => `${s.getAttribute('class') || '(no class)'} => ${Math.round(s.getBoundingClientRect().width)}px`)"""
        )
        check(f"页面无失控尺寸的图标（{big[:2] if big else '无'}）", not big)

        # E5. 可见图片必须都有 alt（装饰图必须显式 alt=""）
        no_alt = page.evaluate(
            "() => [...document.querySelectorAll('img')].filter(i => !i.hasAttribute('alt')).length"
        )
        check("所有 <img> 都带 alt 属性（装饰图显式空 alt）", no_alt == 0)

        # ================= D. 主题令牌 =================
        print("\n== D. 主题令牌 ==")
        # 评论区「点赞 / 删除」的悬停底色必须**取自 --c-clay 令牌**：
        # 旧代码写死 #FBE9EB（浅粉），切到深色仍然照用，在黑底上闪出一块亮色
        for theme, label in (("light", "浅色"), ("dark", "深色")):
            page.emulate_media(color_scheme=theme)
            page.goto(f"{FRONT}/project/{pid}", wait_until="networkidle")
            page.wait_for_timeout(500)
            page.screenshot(path=f"{SHOTS}/audit-detail-{theme}.png")

            body_bg = page.evaluate("() => getComputedStyle(document.body).backgroundColor")
            check(
                f"{label}主题下页面底色正确（{body_bg}）",
                _is_dark(body_bg) if theme == "dark" else not _is_dark(body_bg),
            )

            like = page.locator("[data-test='comment-like']").first
            like.hover()
            page.wait_for_timeout(250)
            res = like.evaluate(HOVER_VS_TOKEN)
            check(
                f"{label}下点赞悬停底色取自 --c-clay 令牌（{res['bg']}）",
                res["bg"] == res["expect"],
            )
            if theme == "dark":
                page.screenshot(path=f"{SHOTS}/audit-comment-hover-dark.png")

        ctx.close()

        # ================= C. 响应式 =================
        print("\n== C. 响应式宽度巡检 ==")
        for w, h, name in WIDTHS:
            ctx = browser.new_context(viewport={"width": w, "height": h})
            page = attach(ctx.new_page())
            for path, label, slug in [
                ("/", "首页", "home"),
                (f"/project/{pid}", "详情页", "detail"),
                ("/profile", "个人中心", "profile"),
            ]:
                # 各档宽度都注入登录态，避免受限页被重定向而测不到真实布局
                inject_login(page, owner["token"], owner["user"])
                take(page, path, f"{label} @{w}px", shot=f"audit-{name}-{slug}.png")
            ctx.close()

        # ================= F. 窄屏导航栏交互 =================
        print("\n== F. 窄屏导航栏 ==")
        ctx = browser.new_context(viewport={"width": 390, "height": 844})
        page = attach(ctx.new_page())
        inject_login(page, owner["token"], owner["user"])

        page.goto(f"{FRONT}/", wait_until="networkidle")
        page.wait_for_timeout(600)
        account_btn = page.locator("header [aria-label='账号菜单']")
        check("窄屏用户名收起、只留头像", account_btn.inner_text().strip() == owner["username"][0].upper())

        page.locator("header [aria-label='通知']").click()
        page.wait_for_timeout(1400)
        check(f"窄屏点铃铛直接进通知页（{page.url.split('/', 3)[-1]}）", "/notifications" in page.url)
        check("进入通知页后无横向溢出", overflow(page) <= 1)
        page.screenshot(path=f"{SHOTS}/audit-mobile-notifications.png")

        page.goto(f"{FRONT}/", wait_until="networkidle")
        page.wait_for_timeout(600)
        page.locator("header [aria-label='账号菜单']").click()
        page.wait_for_timeout(500)
        check("窄屏用户菜单可展开", page.locator("header >> text=退出登录").count() >= 1)
        check("菜单展开后仍无横向溢出", overflow(page) <= 1)
        page.screenshot(path=f"{SHOTS}/audit-mobile-menu.png")

        # 桌面端用户名要完整显示，别为了修窄屏把桌面也砍了
        ctx2 = browser.new_context(viewport={"width": 1440, "height": 900})
        page2 = attach(ctx2.new_page())
        inject_login(page2, owner["token"], owner["user"])
        page2.goto(f"{FRONT}/", wait_until="networkidle")
        page2.wait_for_timeout(500)
        check(
            "宽屏用户名照常显示",
            owner["username"] in page2.locator("header [aria-label='账号菜单']").inner_text(),
        )
        ctx2.close()
        ctx.close()

        browser.close()


def _rgb(rgb):
    """rgb(...) / rgba(...) -> [r, g, b]（越界一律当浅色处理，宁可误报）"""
    body = rgb[rgb.index("(") + 1 : rgb.rindex(")")]
    parts = [p.strip() for p in body.split(",")]
    try:
        if len(parts) >= 4 and float(parts[3]) == 0:
            return None  # 完全透明：没有「闪出一块亮色」的风险
        return [int(float(p)) for p in parts[:3]]
    except ValueError:
        return [255, 255, 255]


def _is_dark(rgb):
    """判断 rgb(...) 是否为深色底（完全透明视为不是深色底）"""
    nums = _rgb(rgb)
    return bool(nums) and sum(nums) / 3 < 110


if __name__ == "__main__":
    try:
        main()
    finally:
        for pid in PIDS:
            cleanup_project(pid)
        if UIDS:
            cleanup_users(UIDS)
        print("已清理临时数据")
    finish()
