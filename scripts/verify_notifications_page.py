# -*- coding: utf-8 -*-
"""独立通知页验证

覆盖：
1) 全部视图列出通知，含 comment / participate 两类文案
2) 未读分段过滤（URL 带 filter=unread）
3) 点击一条 -> 标为已读 + 跳转项目，回到未读视图后该条移出
4) 顶栏面板「查看全部通知」入口

自给自足：A 建项目；B 评论、C 参与 -> A 共 2 条未读（覆盖两类通知）。
"""
import time

from playwright.sync_api import sync_playwright

from _verify_common import (
    FRONT,
    SETTLE,
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
    a, b, c = register("nfpagea"), register("nfpageb"), register("nfpagec")
    pid = create_project(a["token"], f"通知页验证项目 {a['username']}")
    print("临时项目", pid, "用户", a["uid"], b["uid"], c["uid"])

    try:
        api(f"/projects/{pid}/comments", {"content": "用于通知页验证的评论。"}, token=b["token"])
        api(f"/projects/{pid}/participate", {}, token=c["token"])
        time.sleep(SETTLE)

        rows = api("/notifications", token=a["token"])["data"]["notifications"]
        check("通知接口返回 2 条", len(rows) == 2)
        check("覆盖 comment 与 participate 两类", {r["type"] for r in rows} == {"comment", "participate"})

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = attach(browser.new_page(viewport={"width": 1280, "height": 950}, device_scale_factor=2))
            inject_login(page, a["token"], a["user"])

            page.goto(f"{FRONT}/notifications", wait_until="networkidle")
            page.wait_for_timeout(1700)
            rows_ui = page.locator("[data-test='notif-row']")
            check("标题为「通知」", page.locator("h1").inner_text().strip() == "通知")
            check("通知页列出 2 条", rows_ui.count() == 2)
            check("有评论通知文案", rows_ui.filter(has_text="评论了你的项目").count() == 1)
            check("有参与通知文案", rows_ui.filter(has_text="参与了你的项目").count() == 1)
            page.screenshot(path="docs/screenshots/notifications-page-light.png")

            page.get_by_role("button", name="未读", exact=True).click()
            page.wait_for_timeout(1400)
            check("未读视图 2 条", page.locator("[data-test='notif-row']").count() == 2)
            check("URL 带 filter=unread", "filter=unread" in page.url)
            page.screenshot(path="docs/screenshots/notifications-unread-light.png")

            page.locator("[data-test='notif-row']").first.click()
            page.wait_for_timeout(1500)
            check(f"点击后跳转项目详情（{page.url}）", f"/project/{pid}" in page.url)

            page.goto(f"{FRONT}/notifications?filter=unread", wait_until="networkidle")
            page.wait_for_timeout(1500)
            check("已读后未读视图剩 1 条", page.locator("[data-test='notif-row']").count() == 1)

            page.locator("button[title='通知']").click()
            page.wait_for_selector("[data-test='notif-panel']", timeout=3000)
            page.wait_for_timeout(500)
            check("面板有「查看全部通知」入口", page.locator("[data-test='notif-panel'] a", has_text="查看全部通知").count() == 1)
            page.screenshot(path="docs/screenshots/notifications-panel-footer-light.png")
            browser.close()
    finally:
        cleanup_project(pid, [a["uid"], b["uid"], c["uid"]])
        print("残留项目:", sql_one(f"SELECT COUNT(*) FROM projects WHERE id = {pid}"))

    finish()


if __name__ == "__main__":
    main()
