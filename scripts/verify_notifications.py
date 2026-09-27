# -*- coding: utf-8 -*-
"""顶栏铃铛通知面板验证

覆盖：
1) 未读徽标显示条数
2) 面板列出通知，文案含触发者与项目名
3) 点击通知落到项目详情（评论类带 #comments 锚点）
4) 全部标为已读后徽标消失

自给自足：临时账号 A 建项目，临时账号 B 评论 -> A 收到 1 条 comment 通知。
"""
from playwright.sync_api import sync_playwright

from _verify_common import (
    FRONT,
    api,
    attach,
    check,
    cleanup_project,
    create_project,
    finish,
    inject_login,
    register,
    sql_one,
)


def main():
    a, b = register("notifa"), register("notifb")
    pid = create_project(a["token"], f"通知面板验证项目 {a['username']}")
    print("临时项目", pid, "用户", a["uid"], b["uid"])

    try:
        api(f"/projects/{pid}/comments", {"content": "这条评论会触发一条站内通知。"}, token=b["token"])
        check("发起人未读数为 1", api("/notifications/unread-count", token=a["token"])["data"]["unread"] == 1)

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = attach(browser.new_page(viewport={"width": 1280, "height": 900}, device_scale_factor=2))
            inject_login(page, a["token"], a["user"])
            page.goto(f"{FRONT}/", wait_until="networkidle")
            page.wait_for_timeout(1600)

            badge = page.locator("[data-test='unread-badge']")
            check("顶栏未读徽标显示 1", badge.count() == 1 and badge.inner_text().strip() == "1")

            page.locator("button[title='通知']").click()
            page.wait_for_selector("[data-test='notif-panel']", timeout=3000)
            page.wait_for_timeout(600)
            items = page.locator("[data-test='notif-item']")
            check("面板列出 1 条通知", items.count() == 1)
            text = items.first.inner_text()
            check("面板文案含触发者用户名", b["username"] in text)
            check("面板文案含项目名", a["username"] in text)
            page.screenshot(path="docs/screenshots/notifications-light.png")

            items.first.click()
            page.wait_for_timeout(1400)
            check(f"点击后落到项目详情（{page.url}）", f"/project/{pid}" in page.url)
            check("评论类通知带 #comments 锚点", "#comments" in page.url)

            api("/notifications/read", {"all": True}, token=a["token"])
            page.goto(f"{FRONT}/", wait_until="networkidle")
            page.wait_for_timeout(1500)
            check("全部已读后徽标消失", page.locator("[data-test='unread-badge']").count() == 0)
            browser.close()
    finally:
        cleanup_project(pid, [a["uid"], b["uid"]])
        print("残留项目:", sql_one(f"SELECT COUNT(*) FROM projects WHERE id = {pid}"))

    finish()


if __name__ == "__main__":
    main()
