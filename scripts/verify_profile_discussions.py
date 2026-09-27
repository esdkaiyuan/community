# -*- coding: utf-8 -*-
"""个人中心「我参与的讨论」验证

覆盖：
1) GET /users/me/comments 返回本人评论（含回复），带项目信息
2) GET /users/me/stats 的 commentCount 口径一致
3) 个人中心讨论分区计数与卡片数
4) 点击讨论卡落到该项目评论区（#comments）

自给自足：临时账号 A 建项目，留 1 根评论 + 1 回复。
"""
from playwright.sync_api import sync_playwright

from _verify_common import (
    FRONT,
    api,
    attach,
    check,
    cleanup_project,
    comment,
    create_project,
    finish,
    inject_login,
    register,
    sql_one,
)


def main():
    a = register("profdisc")
    pid = create_project(a["token"], f"讨论验证项目 {a['username']}")
    print("临时项目", pid, "用户", a["uid"])

    try:
        root = comment(a["token"], pid, "第一条讨论内容，用来验证个人中心的讨论分区。")
        comment(a["token"], pid, "第二条是回复，同样会出现在讨论列表里。", parent_id=root["id"])

        mine = api("/users/me/comments", token=a["token"])["data"]
        check("接口返回 2 条我的讨论", len(mine["comments"]) == 2)
        check("每条都带项目信息", all(c.get("project", {}).get("id") == pid for c in mine["comments"]))
        check("其中一条是回复", sum(1 for c in mine["comments"] if c.get("parentId")) == 1)
        check("统计接口 commentCount 为 2", api("/users/me/stats", token=a["token"])["data"]["commentCount"] == 2)

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = attach(browser.new_page(viewport={"width": 1280, "height": 950}, device_scale_factor=2))
            inject_login(page, a["token"], a["user"])
            page.goto(f"{FRONT}/profile", wait_until="networkidle")
            page.wait_for_timeout(1700)

            heading = page.get_by_role("heading", name="我参与的讨论")
            heading.scroll_into_view_if_needed()
            page.wait_for_timeout(1500)
            check("讨论分区标题显示（2）", "（2）" in heading.inner_text())
            cards = page.locator("[data-test='profile-discussion']")
            check("讨论卡 2 张", cards.count() == 2)
            check("卡片含项目名", any(a["username"] in cards.nth(i).inner_text() for i in range(cards.count())))
            page.screenshot(path="docs/screenshots/profile-discussions-light.png")

            cards.first.click()
            page.wait_for_timeout(1500)
            check(f"点击讨论卡落该项目评论区（{page.url}）", f"/project/{pid}" in page.url and "#comments" in page.url)
            browser.close()
    finally:
        cleanup_project(pid, [a["uid"]])
        print("残留项目:", sql_one(f"SELECT COUNT(*) FROM projects WHERE id = {pid}"))

    finish()


if __name__ == "__main__":
    main()
