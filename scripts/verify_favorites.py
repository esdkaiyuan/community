# -*- coding: utf-8 -*-
"""收藏闭环验证：详情页操作卡 / 顶部玻璃条书签 / 个人中心「我的收藏」/ 取消收藏

覆盖：
1) API：收藏后 /users/me/favorites 计数与详情接口 favorited 标记
2) 详情页操作卡出现「已收藏」按钮
3) 个人中心「我的收藏」分区计数与卡片数
4) 就地取消收藏后卡片即时移出、服务端同步

自给自足：临时账号 A 建 2 个项目并收藏。
"""
from playwright.sync_api import sync_playwright

from _verify_common import (
    FRONT,
    api,
    attach,
    check,
    cleanup_project,
    cleanup_users,
    create_project,
    finish,
    inject_login,
    register,
    sql_one,
)


def main():
    a = register("favdetail")
    p1 = create_project(a["token"], f"收藏验证项目一 {a['username']}")
    p2 = create_project(a["token"], f"收藏验证项目二 {a['username']}")
    print("临时项目", p1, p2, "用户", a["uid"])

    try:
        for pid in (p1, p2):
            api(f"/projects/{pid}/favorite", {}, token=a["token"])
        check("接口返回 2 条收藏", api("/users/me/favorites", token=a["token"])["data"]["total"] == 2)
        check("详情接口标记 favorited", api(f"/projects/{p1}", token=a["token"])["data"]["favorited"] is True)

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = attach(browser.new_page(viewport={"width": 1280, "height": 950}, device_scale_factor=2))
            inject_login(page, a["token"], a["user"])

            # 详情页：滚动过封面让玻璃条浮现，操作卡显示「已收藏」
            page.goto(f"{FRONT}/project/{p1}", wait_until="networkidle")
            page.wait_for_timeout(1600)
            check("详情页操作卡出现「已收藏」", page.get_by_role("button", name="已收藏", exact=True).count() == 1)
            page.mouse.wheel(0, 700)
            page.wait_for_timeout(1200)
            page.screenshot(path="docs/screenshots/favorite-detail-light.png")

            # 个人中心「我的收藏」
            page.goto(f"{FRONT}/profile", wait_until="networkidle")
            page.wait_for_timeout(1800)
            heading = page.get_by_role("heading", name="我的收藏")
            heading.scroll_into_view_if_needed()
            page.wait_for_timeout(1500)
            check("收藏分区标题显示（2）", "（2）" in heading.inner_text())
            box = page.locator("[data-test='profile-favorites']")
            check("收藏卡 2 张", box.locator("article").count() == 2)
            page.screenshot(path="docs/screenshots/favorite-profile-light.png")

            # 就地取消收藏
            box.locator("article button[aria-label='取消收藏']").first.click()
            page.wait_for_timeout(1300)
            check("取消后卡片即时移出", box.locator("article").count() == 1)
            check(
                "服务端该收藏已移除",
                all(x["id"] != p1 for x in api("/users/me/favorites", token=a["token"])["data"]["projects"]),
            )
            browser.close()
    finally:
        cleanup_project(p1)
        cleanup_project(p2)
        cleanup_users([a["uid"]])
        print("残留:", sql_one(f"SELECT COUNT(*) FROM projects WHERE id IN ({p1},{p2})"))

    finish()


if __name__ == "__main__":
    main()
