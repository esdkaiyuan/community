# -*- coding: utf-8 -*-
"""评论两级结构验证（根评论 + 回复）

覆盖：
1) API：根评论 1 条，replyCount 与 replies 长度一致
2) 回复的回复会**展平**挂到根评论下（parentId 指向根）
3) 前端：渲染 1 个根评论项 + 2 条缩进回复

自给自足：临时账号 A 建项目，发 1 根评论 + 2 条回复（其中一条是回复的回复）。
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
    a = register("ufreply")
    pid = create_project(a["token"], f"两级回复验证项目 {a['username']}")
    print("临时项目", pid, "用户", a["uid"])

    try:
        root = comment(a["token"], pid, "根评论：外观应与 App Store 评价列表一致。")
        r1 = comment(a["token"], pid, "回复一：挂在根评论的缩进线上。", parent_id=root["id"])
        comment(a["token"], pid, "回复二：回复的回复也会展平到根评论下。", parent_id=r1["id"])

        data = api(f"/projects/{pid}/comments")["data"]
        check("根评论 1 条", len(data["comments"]) == 1)
        item = data["comments"][0]
        check("replyCount 为 2", item["replyCount"] == 2)
        check("replies 返回 2 条", len(item["replies"]) == 2)
        check("展平后 parentId 都指向根评论", all(r["parentId"] == item["id"] for r in item["replies"]))

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = attach(browser.new_page(viewport={"width": 1280, "height": 950}, device_scale_factor=2))
            inject_login(page, a["token"], a["user"])
            page.goto(f"{FRONT}/project/{pid}", wait_until="networkidle")
            page.wait_for_timeout(1500)
            page.locator("[data-test='comment-item']").first.scroll_into_view_if_needed()
            page.wait_for_timeout(1600)

            check("页面渲染 1 个根评论项", page.locator("[data-test='comment-item']").count() == 1)
            replies = page.locator("[data-test='comment-reply']")
            check("页面渲染 2 条回复", replies.count() == 2)
            border = replies.first.evaluate("el => getComputedStyle(el.parentElement).borderLeftWidth")
            check(f"回复容器带缩进竖线（borderLeft={border}）", border not in ("0px", ""))
            page.screenshot(path="docs/screenshots/replies-light.png")
            browser.close()
    finally:
        cleanup_project(pid, [a["uid"]])
        print("残留项目:", sql_one(f"SELECT COUNT(*) FROM projects WHERE id = {pid}"))

    finish()


if __name__ == "__main__":
    main()
