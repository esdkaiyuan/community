# -*- coding: utf-8 -*-
"""评论模块总验证：CRUD / 权限矩阵 / rootTotal 分家 / 级联删除 / 页面交互

与既有脚本互补（不重复）：
- verify_replies.py          两级结构与展平
- verify_comment_likes.py    点赞
- verify_comment_deeplink.py 深链定位

本脚本四段：
A. API 权限与校验（不改数量）：游客发/删 401；空内容、纯 emoji、501 字 400；
   非作者非项目主删 403；删不存在 404
B. rootTotal 与 total 分家：total 含回复、rootTotal 只算根（假「加载更多」的根治点）
C. 删除正例、级联与计数同步：项目主删他人 200、作者删自己 200；删带回复的根评论
   → 库中零孤儿（自引用 FK 级联，schema.sql 曾漏）；projects.comment_count 全程精确
D. 页面交互（PAGE_SIZE=10）：游客登录提示/无输入框；「显示更多评论」点完即消失
   （12 根 + 1 回复 → total=13 ≠ rootTotal=12，旧代码拿 total 判断按钮永远点不完）；
   登录后字数计数 0/500→4/500、maxlength=500、空草稿禁用、发表置顶、删除按钮只属于自己

自给自足：临时账号 A 建项目，B 参与互动，finally 全清。
"""
from playwright.sync_api import sync_playwright

from _verify_common import (
    FRONT,
    api,
    api_status,
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

LONG_TEXT = "评" * 501  # 上限 500，超 1 字即拒


def rows(pid):
    return sql_one(f"SELECT COUNT(*) FROM project_comments WHERE project_id = {pid}")


def main():
    a, b = register("vcomta"), register("vcomtb")
    pid = create_project(a["token"], f"评论总验证项目 {a['username']}")
    print("临时项目", pid, "账号", a["uid"], b["uid"])

    try:
        # ---------- 造数：12 根 + 1 回复（回复挂 roots[-1]） ----------
        roots = [comment(a["token"], pid, f"根评论 {i:02d}。") for i in range(1, 13)]
        comment(b["token"], pid, "回复：挂在最后一个根评论下。", parent_id=roots[-1]["id"])
        check("造数后 total=13", api(f"/projects/{pid}/comments")["data"]["total"] == 13)

        # ---------- A. 权限与校验（不改数量） ----------
        print("-- A. API 权限与校验 --")
        st, _ = api_status(f"/projects/{pid}/comments", {"content": "游客想发言"})
        check("游客发评论 401", st == 401)
        st, _ = api_status(f"/projects/{pid}/comments/{roots[0]['id']}", method="DELETE")
        check("游客删评论 401", st == 401)
        st, _ = api_status(f"/projects/{pid}/comments", {"content": ""}, token=b["token"])
        check("空内容 400", st == 400)
        st, _ = api_status(f"/projects/{pid}/comments", {"content": "👍"}, token=b["token"])
        check("纯 emoji（净化后为空）400", st == 400)
        st, body = api_status(f"/projects/{pid}/comments", {"content": LONG_TEXT}, token=b["token"])
        check("501 字超长 400（提示含 500）", st == 400 and "500" in body.get("message", ""))
        st, _ = api_status(f"/projects/{pid}/comments/{roots[0]['id']}", token=b["token"], method="DELETE")
        check("非作者非项目主删评论 403", st == 403)
        st, _ = api_status(f"/projects/{pid}/comments/99999999", token=a["token"], method="DELETE")
        check("删不存在的评论 404", st == 404)

        # ---------- B. rootTotal 与 total 分家 ----------
        print("-- B. rootTotal 与 total 分家 --")
        data = api(f"/projects/{pid}/comments")["data"]
        check("total=13（含回复）", data["total"] == 13)
        check("rootTotal=12（只算根）", data["rootTotal"] == 12)
        check("默认页返回全部 12 根", len(data["comments"]) == 12)

        # ---------- C. 删除正例、级联与计数同步 ----------
        print("-- C. 删除正例、级联与计数同步 --")
        check("发 13 条后 comment_count=13", sql_one(f"SELECT comment_count FROM projects WHERE id = {pid}") == "13")

        res = api(f"/projects/{pid}/comments", {"content": "B 的合法评论。"}, token=b["token"])["data"]
        b_cid = res["comment"]["id"]
        check("B 发评论成功 commentCount=14", res["commentCount"] == 14)

        st, _ = api_status(f"/projects/{pid}/comments/{b_cid}", token=a["token"], method="DELETE")
        check("项目主删他人评论 200", st == 200)
        check("删后 comment_count=13", sql_one(f"SELECT comment_count FROM projects WHERE id = {pid}") == "13")

        st, body = api_status(f"/projects/{pid}/comments/{roots[-1]['id']}", token=a["token"], method="DELETE")
        check("项目主删带回复的根评论 200", st == 200)
        check("删除返回 commentCount=11", body.get("data", {}).get("commentCount") == 11)
        check(f"删根后库中零孤儿（{rows(pid)} 行 = 11）", rows(pid) == "11")
        data = api(f"/projects/{pid}/comments")["data"]
        check("rootTotal/total 同步为 11", data["rootTotal"] == 11 and data["total"] == 11)

        res = api(f"/projects/{pid}/comments", {"content": "B 再发一条再自己删。"}, token=b["token"])["data"]
        st, _ = api_status(f"/projects/{pid}/comments/{res['comment']['id']}", token=b["token"], method="DELETE")
        check("作者删自己评论 200", st == 200)
        check("计数回到 11", sql_one(f"SELECT comment_count FROM projects WHERE id = {pid}") == "11")

        st, _ = api_status(f"/projects/{pid}/comments/{roots[0]['id']}", token=a["token"], method="DELETE")
        check("作者删自己根评论（无回复）200", st == 200)
        check("最终 10 根 0 回复，行数=10", rows(pid) == "10")

        # ---------- D. 页面交互 ----------
        print("-- D. 页面交互 --")
        # 补数：2 根 + 1 回复（挂 roots[1]，最老、在第二页）→ 12 根 + 1 回复
        comment(a["token"], pid, "补数根 1。")
        comment(a["token"], pid, "补数根 2。")
        comment(b["token"], pid, "回复：为分页红线再造。", parent_id=roots[1]["id"])
        data = api(f"/projects/{pid}/comments")["data"]
        check("补数后 total=13 / rootTotal=12 分家", data["total"] == 13 and data["rootTotal"] == 12)

        with sync_playwright() as p:
            browser = p.chromium.launch()

            # 游客视角：提示可见、无输入框；分页按钮点完即消失
            guest = attach(browser.new_page(viewport={"width": 1280, "height": 950}))
            guest.goto(f"{FRONT}/project/{pid}", wait_until="networkidle")
            guest.wait_for_timeout(1500)
            guest.locator("h2", has_text="评论").first.scroll_into_view_if_needed()
            guest.wait_for_timeout(1200)
            check("游客见登录提示", guest.locator("[data-test='comment-login-hint']").is_visible())
            check("游客无输入框", guest.locator("[data-test='comment-input']").count() == 0)
            check("首页渲染 10 根", guest.locator("[data-test='comment-item']").count() == 10)
            more = guest.get_by_role("button", name="显示更多评论")
            check("分页按钮可见（10 < rootTotal 12）", more.is_visible())
            more.click()
            guest.wait_for_timeout(1500)
            check("点完后渲染 12 根 + 1 回复",
                  guest.locator("[data-test='comment-item']").count() == 12
                  and guest.locator("[data-test='comment-reply']").count() == 1)
            # 红线：total=13 ≠ rootTotal=12 —— 旧代码 12 < 13，按钮永远点不完
            check("点完全部根评论后按钮消失", guest.get_by_role("button", name="显示更多评论").count() == 0)
            guest.close()

            # 登录视角（B）：输入 / 计数 / 提交 / 删除按钮归属
            page = attach(browser.new_page(viewport={"width": 1280, "height": 950}, device_scale_factor=2))
            inject_login(page, b["token"], b["user"])
            page.goto(f"{FRONT}/project/{pid}", wait_until="networkidle")
            page.wait_for_timeout(1500)
            page.locator("h2", has_text="评论").first.scroll_into_view_if_needed()
            page.wait_for_timeout(1200)
            check("登录后无登录提示", page.locator("[data-test='comment-login-hint']").count() == 0)
            box = page.locator("[data-test='comment-input']")
            counter = page.locator("[data-test='comment-counter']")
            submit = page.locator("[data-test='comment-submit']")
            check("输入框可见", box.is_visible())
            check("maxlength=500", box.get_attribute("maxlength") == "500")
            check("初始计数 0/500", counter.inner_text().strip() == "0/500")
            check("空草稿提交禁用", submit.is_disabled())
            box.fill("你好世界")
            page.wait_for_timeout(300)
            check("输入后计数 4/500", counter.inner_text().strip() == "4/500")
            check("有草稿后提交可用", not submit.is_disabled())
            submit.click()
            page.wait_for_timeout(1800)
            first_item = page.locator("[data-test='comment-item']").first
            check("新评论置顶上墙", "你好世界" in first_item.inner_text())
            check("提交后草稿清零", counter.inner_text().strip() == "0/500")
            check("B 视角删除按钮只有 1 个（自己的）", page.locator("[data-test='comment-delete']").count() == 1)
            check("删除按钮就在自己的评论上", first_item.locator("[data-test='comment-delete']").count() == 1)
            page.screenshot(path="docs/screenshots/comments-overview.png")
            browser.close()
    finally:
        cleanup_project(pid, [a["uid"], b["uid"]])
        print("残留项目:", sql_one(f"SELECT COUNT(*) FROM projects WHERE id = {pid}"))
        print("残留用户:", sql_one(f"SELECT COUNT(*) FROM users WHERE id IN ({a['uid']},{b['uid']})"))

    finish()


if __name__ == "__main__":
    main()
