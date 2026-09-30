# -*- coding: utf-8 -*-
"""
移动端触控细节验证（390×844 视口 + 1440 桌面对照）

A. 触屏热区 ≥ 44px：视觉盒不变，靠 ::after 伪元素扩展命中区——
   用 elementFromPoint 在按钮「盒边外」做真实命中探测（伪元素参与命中测试），
   并同时断言视觉尺寸没变（热区扩大 ≠ 按钮变大）
   覆盖：评论行内三按钮（点赞/回复/删除）、卡片收藏、header 铃铛与账号菜单、分页按钮
B. iOS 聚焦缩放防线：小屏（≤640px）输入类字号 ≥ 16px（<16px 时 iOS Safari
   聚焦输入框会自动放大整个页面）；桌面视口保持原字号视觉不变
C. 双击缩放防线：button 的 touch-action 为 manipulation（快速连点收藏/点赞
   不应触发页面缩放）
D. 零 console 错误

探测两个硬教训（首轮红证实测）：
① 探测点必须以「盒边」为基准——用「盒中心 ± 偏移」时，36px 高的按钮偏 5px
  仍在盒内，热区没扩展也假绿；
② 探测前必须 scrollIntoViewIfNeeded——elementFromPoint 对视口外坐标返回
  null，页面下方的评论按钮会假红。
"""
from playwright.sync_api import sync_playwright

from _verify_common import (
    FRONT,
    api,
    check,
    cleanup_project,
    cleanup_users,
    comment,
    create_project,
    finish,
    inject_login,
    register,
    sql_one,
)

PIDS = []
UIDS = []

# 命中探测：问浏览器「按钮盒边外 off 像素的那一点上是谁」。
# side ∈ up/down/left/right，探测点从对应盒边向外推 off 像素。
HIT_JS = """([sel, side, off]) => {
  const el = document.querySelector(sel);
  if (!el) return null;
  el.scrollIntoView({ block: 'center', behavior: 'instant' });
  const r = el.getBoundingClientRect();
  if (r.width === 0 && r.height === 0) return null;
  const cx = r.x + r.width / 2;
  const cy = r.y + r.height / 2;
  const px = side === 'left' ? r.x - off : side === 'right' ? r.right + off : cx;
  const py = side === 'up' ? r.y - off : side === 'down' ? r.bottom + off : cy;
  const hit = document.elementFromPoint(px, py);
  return hit === el || el.contains(hit);
}"""

FONT_JS = """([sel]) => {
  const el = document.querySelector(sel);
  return el ? parseFloat(getComputedStyle(el).fontSize) : null;
}"""

TOUCH_JS = """([sel]) => {
  const el = document.querySelector(sel);
  return el ? getComputedStyle(el).touchAction : null;
}"""


def hits(page, sel, side, off):
    return page.evaluate(HIT_JS, [sel, side, off])


def font_of(page, sel):
    return page.evaluate(FONT_JS, [sel])


def touch_of(page, sel):
    return page.evaluate(TOUCH_JS, [sel])


def visual_height(page, sel):
    loc = page.locator(sel).first
    if loc.count() == 0:
        return None
    b = loc.bounding_box()
    return b["height"] if b else None


def main():
    # ---- 造数：创建者 + 评论者 + 项目 + 根评论 + 补齐分页 ----
    creator = register("mta")
    UIDS.append(creator["uid"])
    commenter = register("mtb")
    UIDS.append(commenter["uid"])
    pid = create_project(creator["token"], "移动端触控验证项目")
    PIDS.append(pid)
    comment(commenter["token"], pid, "移动端验证用根评论：热区与字号探测目标。")

    # 补齐到 13 个在架项目，逼出广场分页（每页 12 个）
    total = int(api("/projects?page=1&pageSize=1")["data"]["total"])
    for i in range(max(0, 13 - total)):
        PIDS.append(create_project(creator["token"], f"移动端分页填充项目 {i}"))

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        console_errors = []
        try:
            page = browser.new_page(viewport={"width": 390, "height": 844})
            page.on(
                "console",
                lambda m: console_errors.append(m.text) if m.type == "error" else None,
            )
            inject_login(page, commenter["token"], commenter["user"])

            print("\n== A. 触屏热区：盒边外命中（::after 扩展区）+ 视觉尺寸不变 ==")
            # 详情页：评论行内按钮。行内 gap-0.5，只扩垂直方向（水平扩展会互吃热区）。
            page.goto(f"{FRONT}/project/{pid}", wait_until="networkidle")
            inline_buttons = [
                ("[data-test='comment-like']", "评论点赞按钮"),
                ("[data-test='comment-reply-btn']", "评论回复按钮"),
                ("[data-test='comment-delete']", "评论删除按钮"),
            ]
            for sel, name in inline_buttons:
                check(f"{name}：盒上方 7px 命中（垂直热区扩展）", hits(page, sel, "up", 7) is True)
                check(f"{name}：盒下方 7px 命中（垂直热区扩展）", hits(page, sel, "down", 7) is True)
                h = visual_height(page, sel)
                check(f"{name}：视觉盒不变（高 ≤ 26px，实测 {h}）", h is not None and h <= 26)

            check("评论删除：touch-action 为 manipulation", touch_of(page, "[data-test='comment-delete']") == "manipulation")

            # 广场：卡片收藏按钮 28×28，热区四向扩 8px → 44×44
            page.goto(f"{FRONT}/", wait_until="networkidle")
            fav = "[data-test='card-fav']"
            check("卡片收藏：盒上方 6px 命中", hits(page, fav, "up", 6) is True)
            check("卡片收藏：盒下方 6px 命中", hits(page, fav, "down", 6) is True)
            check("卡片收藏：盒右侧 6px 命中", hits(page, fav, "right", 6) is True)
            loc = page.locator(fav).first
            b = loc.bounding_box() if loc.count() else None
            check(
                f"卡片收藏：视觉盒仍是 28×28（实测 {b['width'] if b else None}×{b['height'] if b else None}）",
                b is not None and abs(b["width"] - 28) <= 1 and abs(b["height"] - 28) <= 1,
            )
            check("卡片收藏：touch-action 为 manipulation（防双击缩放）", touch_of(page, fav) == "manipulation")

            # header：铃铛 36→48、账号菜单 40→48
            check("通知铃铛：盒上方 5px 命中", hits(page, "button[aria-label='通知']", "up", 5) is True)
            check("通知铃铛：视觉盒不变（高 ≤ 36px）", (visual_height(page, "button[aria-label='通知']") or 99) <= 36)
            check("账号菜单：盒上方 3px 命中", hits(page, "button[aria-label='账号菜单']", "up", 3) is True)

            # 分页按钮：36 高，垂直扩 8px；水平不扩（相邻按钮 gap 仅 6px）
            pag = "[data-test='page-btn'].is-active"
            check("分页按钮存在（补齐后广场应有第 2 页）", page.locator(pag).count() >= 1)
            check("分页按钮：盒上方 4px 命中", hits(page, pag, "up", 4) is True)
            check("分页按钮：视觉盒不变（高 ≤ 36px）", (visual_height(page, pag) or 99) <= 36)

            print("\n== B. iOS 聚焦缩放防线：小屏输入字号 ≥ 16px ==")
            # /login 对已登录用户会被路由守卫重定向——登录字号检查必须用
            # 全新上下文（无 token）。主 page 的 localStorage 里已有登录态。
            mctx = browser.new_context(viewport={"width": 390, "height": 844})
            mpage = mctx.new_page()
            mpage.goto(f"{FRONT}/login", wait_until="networkidle")
            fs = font_of(mpage, "#email")
            check(f"登录页输入框字号 ≥ 16px（实测 {fs}）", fs is not None and fs >= 16)
            mctx.close()
            page.goto(f"{FRONT}/project/{pid}", wait_until="networkidle")
            try:
                page.wait_for_selector("[data-test='comment-input']", timeout=8000)
            except Exception:
                # 偶发水合竞态：重载一次再等；仍缺则如实红
                page.reload(wait_until="networkidle")
                page.wait_for_selector("[data-test='comment-input']", timeout=10000)
            fs = font_of(page, "[data-test='comment-input']")
            check(f"评论输入框字号 ≥ 16px（实测 {fs}）", fs is not None and fs >= 16)

            print("\n== B2. 桌面对照：输入字号视觉不变 ==")
            dctx = browser.new_context(viewport={"width": 1440, "height": 900})
            dpage = dctx.new_page()
            dpage.goto(f"{FRONT}/login", wait_until="networkidle")
            fs = font_of(dpage, "#email")
            check(f"桌面输入框字号保持 14px（实测 {fs}）", fs is not None and fs < 16)
            dctx.close()

            print("\n== D. console ==")
            real_errors = [e for e in console_errors if not e.startswith("Failed to load resource")]
            check("零 console 错误", len(real_errors) == 0)
            for e in real_errors[:5]:
                print("  console:", e)
        finally:
            browser.close()

        # ---- 清理：项目级联评论，再删用户 ----
        for p in PIDS:
            cleanup_project(p, UIDS)
        cleanup_users(UIDS)
        print("残留项目:", sql_one(f"SELECT COUNT(*) FROM projects WHERE id IN ({','.join(map(str, PIDS)) or '0'})"))
        print("残留用户:", sql_one(f"SELECT COUNT(*) FROM users WHERE id IN ({','.join(map(str, UIDS)) or '0'})"))

    finish()


if __name__ == "__main__":
    main()
