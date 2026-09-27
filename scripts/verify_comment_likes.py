# -*- coding: utf-8 -*-
"""评论点赞验证：点赞 / 取消点赞 的状态与计数

覆盖：
1) API：点赞后 likeCount=1；带登录态返回 liked=true；游客视角计数一致
2) 前端：按钮 aria-pressed / 心形填充态 / 计数渲染
3) 取消点赞后前后端计数归零

自给自足：临时账号 A 建项目并发根评论；临时账号 B 点赞。
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
    a, b = register("uflikea"), register("uflikeb")
    pid = create_project(a["token"], f"评论点赞验证项目 {a['username']}")
    print("临时项目", pid, "用户", a["uid"], b["uid"])

    try:
        root = comment(a["token"], pid, "根评论：用于验证点赞状态与计数。")
        cid = root["id"]

        like = api(f"/projects/{pid}/comments/{cid}/like", {}, token=b["token"])["data"]
        check("点赞后计数为 1", like["likeCount"] == 1)

        mine = api(f"/projects/{pid}/comments", token=b["token"])["data"]["comments"][0]
        check("带登录态返回 liked=true", mine["liked"] is True)
        check("游客视角计数同样为 1", api(f"/projects/{pid}/comments")["data"]["comments"][0]["likeCount"] == 1)

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = attach(browser.new_page(viewport={"width": 1280, "height": 950}, device_scale_factor=2))
            inject_login(page, b["token"], b["user"])
            page.goto(f"{FRONT}/project/{pid}", wait_until="networkidle")
            page.wait_for_timeout(1500)
            page.locator("[data-test='comment-item']").first.scroll_into_view_if_needed()
            page.wait_for_timeout(1600)

            btn = page.locator("[data-test='comment-like']").first
            check("按钮 aria-pressed=true", btn.get_attribute("aria-pressed") == "true")
            check("点赞计数渲染为 1", btn.inner_text().strip() == "1")
            check("心形为实心", btn.locator("svg").first.get_attribute("fill") == "currentColor")
            page.screenshot(path="docs/screenshots/comment-likes-light.png")

            btn.click()
            page.wait_for_timeout(1200)
            check("取消点赞后 aria-pressed=false", btn.get_attribute("aria-pressed") == "false")
            check("取消后计数不再渲染", btn.inner_text().strip() == "")
            check(
                "服务端计数归零",
                api(f"/projects/{pid}/comments", token=b["token"])["data"]["comments"][0]["likeCount"] == 0,
            )
            browser.close()
    finally:
        cleanup_project(pid, [a["uid"], b["uid"]])
        print("残留项目:", sql_one(f"SELECT COUNT(*) FROM projects WHERE id = {pid}"))

    finish()


if __name__ == "__main__":
    main()
