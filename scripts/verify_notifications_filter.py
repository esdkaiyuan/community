# -*- coding: utf-8 -*-
"""通知中心「类型筛选 + 批量已读」验证

覆盖：
1) 类型筛选：participate / comment / mention 三类各自只出该类；reply 无数据时走空态
2) 非法 type 深链（favorite / <script>）：静默忽略、页面照常渲染、console 零错误
3) 已读状态与类型可组合（filter=unread&type=comment）
4) 选择模式：点击行是勾选而非跳转
5) 批量已读只影响选中项（用数据库 is_read 交叉验证，不信 UI 颜色）
6) 未读视图下批量已读后条目离开列表
7) 全选 / 取消全选
8) 全部标为已读兜底

自给自足：A 建项目；B 评论并 @A（触发 comment + mention）；C 参与（触发
participate）-> A 共 3 条未读，正好覆盖三类。
"""
import time
from urllib.parse import quote

from playwright.sync_api import sync_playwright

from _verify_common import (
    FRONT,
    SETTLE,
    api,
    api_status,
    attach,
    check,
    cleanup_project,
    create_project,
    finish,
    inject_login,
    register,
    sql_one,
)

NOTIF = "/notifications"


def chk(label, cond, actual=""):
    """check 只收两个参数，实际值拼进标签里 —— 断言一红就能直接看出差在哪"""
    check(f"{label}（实际 {actual}）" if actual != "" else label, cond)


def goto(page, query=""):
    page.goto(f"{FRONT}{NOTIF}{query}", wait_until="networkidle")
    page.wait_for_timeout(700)


def rows(page):
    return page.locator("[data-test='notif-row']")


def wait_rows(page, timeout=8000):
    try:
        page.wait_for_selector("[data-test='notif-row']", timeout=timeout)
    except Exception:
        pass
    return rows(page).count()


def unread_in_db(uid):
    return int(sql_one(f"SELECT COUNT(*) FROM notifications WHERE user_id={uid} AND is_read=0") or 0)


def main():
    a, b, c = register("nflta"), register("nfltb"), register("nfltc")
    pid = create_project(a["token"], f"通知筛选验证项目 {a['username']}")
    print("临时项目", pid, "用户", a["uid"], b["uid"], c["uid"])

    try:
        # 一条评论同时触发 comment 与 mention；参与触发 participate —— A 共 3 条
        api(f"/projects/{pid}/comments", {"content": f"@{a['username']} 这条同时触发评论与提及两类通知。"}, token=b["token"])
        api(f"/projects/{pid}/participate", {}, token=c["token"])
        time.sleep(SETTLE)

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context(viewport={"width": 1280, "height": 900})
            page = ctx.new_page()
            attach(page)
            inject_login(page, a["token"], a["user"])

            # ---------- 1) 全部视图基线 ----------
            goto(page)
            n = wait_rows(page)
            chk("全部视图列出 3 条通知", n == 3, f"{n}")
            chk("数据库侧 A 有 3 条未读", unread_in_db(a["uid"]) == 3, f"{unread_in_db(a['uid'])}")

            # ---------- 2) 类型筛选：逐个类型只出该类 ----------
            cases = [
                ("participate", "参与了你的项目", 1),
                ("comment", "评论了你的项目", 1),
                ("mention", "在评论中提及了你", 1),
                ("reply", "回复了你在", 0),
            ]
            for value, text, expect in cases:
                page.locator(f"[data-test='notif-type-chip'][data-value='{value}']").click()
                page.wait_for_timeout(900)
                n = rows(page).count()
                chk(f"类型筛选 {value} 命中 {expect} 条", n == expect, f"{n}")
                if expect:
                    body = page.locator("body").inner_text()
                    chk(f"类型筛选 {value} 行内含「{text}」", text in body)
                else:
                    chk("无该类型时走空态", "没有这类通知" in page.locator("body").inner_text())
                chk(f"类型筛选 {value} 已同步进 URL", f"type={value}" in page.url, page.url)

            # 后端那道白名单必须单独钉：前端自己也有一道白名单，非法值根本传不到后端，
            # 所以 UI 层断言只覆盖了前端那道 —— 后端这道只能直接打 API。
            # 缺失后端白名单时，MySQL 会把非法 ENUM 值比较成空结果，用户看到的是
            # 「没有通知」而不是「筛选没生效」—— 行为错得静悄悄，正是要防的
            for bad in ("favorite", "<script>"):
                status, body = api_status(f"/notifications?type={quote(bad)}", token=a["token"])
                data = body.get("data", {}) if isinstance(body, dict) else {}
                chk(f"API 非法 type={bad} 返回 200（不出 5xx）", status == 200, status)
                chk(f"API 非法 type={bad} 静默忽略为全量 3 条", data.get("total") == 3, data.get("total"))
                chk(f"API 非法 type={bad} 回显 type=all", data.get("type") == "all", data.get("type"))

            # ---------- 3) 非法 type：静默忽略，不出 5xx（前端那道白名单） ----------
            for bad in ("favorite", "%3Cscript%3E"):
                goto(page, f"?type={bad}")
                page.wait_for_timeout(800)
                chk(f"非法 type={bad} 页面仍渲染出列表", rows(page).count() == 3, f"{rows(page).count()}")
                chk(f"非法 type={bad} 未把页面打成错误态", "通知" in page.locator("h1").inner_text())

            # ---------- 4) 已读状态 × 类型 组合 ----------
            goto(page, "?filter=unread&type=comment")
            n = wait_rows(page)
            chk("未读 + comment 组合筛选命中 1 条", n == 1, f"{n}")

            # ---------- 5) 选择模式：点击行是勾选而非跳转 ----------
            goto(page)
            wait_rows(page)
            page.locator("[data-test='notif-select-toggle']").click()
            page.wait_for_timeout(500)
            chk("进入选择模式出现底部操作条", page.locator("[data-test='notif-bulk-bar']").count() == 1)

            page.locator("[data-test='notif-row']").first.click()
            page.wait_for_timeout(400)
            chk("选择模式下点击行是勾选（未跳转）", NOTIF in page.url, page.url)
            chk(
                "勾选后该行勾选圈为选中态",
                page.locator("[data-test='notif-checkbox'][data-selected='1']").count() == 1,
            )
            chk("操作条显示已选 1 条", "已选 1 条" in page.locator("[data-test='notif-bulk-bar']").inner_text())

            page.locator("[data-test='notif-row']").nth(1).click()
            page.wait_for_timeout(400)
            chk(
                "再勾选一条 -> 已选 2 条",
                page.locator("[data-test='notif-checkbox'][data-selected='1']").count() == 2,
            )

            # 点「完成」退出：这一步只验证勾选交互，不应动数据
            page.locator("[data-test='notif-done']").click()
            page.wait_for_timeout(500)
            chk("点完成后退出选择模式且未改数据", unread_in_db(a["uid"]) == 3, f"{unread_in_db(a['uid'])}")

            # ---------- 6) 批量已读只影响选中项 ----------
            # 刻意切到单类型视图再全选：列表按时间倒序，在「全部」视图里按位置勾选到底
            # 勾中哪几条取决于创建时序 —— 直接断言「某条未受影响」会变成掷骰子
            goto(page, "?type=participate")
            wait_rows(page)
            page.locator("[data-test='notif-select-toggle']").click()
            page.wait_for_timeout(500)
            page.locator("[data-test='notif-select-all']").click()
            page.wait_for_timeout(400)
            page.locator("[data-test='notif-bulk-read']").click()
            page.wait_for_timeout(1200)
            chk("批量已读后未读数 3 -> 2", unread_in_db(a["uid"]) == 2, f"{unread_in_db(a['uid'])}")
            chk("批量已读后退出选择模式", page.locator("[data-test='notif-bulk-bar']").count() == 0)

            # 未选中的 comment / mention 必须都还是未读 —— 批量不能误伤
            still = int(
                sql_one(
                    "SELECT COUNT(*) FROM notifications "
                    f"WHERE user_id={a['uid']} AND is_read=0 AND type IN ('comment','mention')"
                )
                or 0
            )
            chk("未勾选的 comment/mention 仍是未读（批量未误伤）", still == 2, f"{still}")

            # ---------- 7) 全选 / 取消全选 ----------
            # 先回全部视图：上一步是在 type=participate 视图里操作的，那里只有 1 条
            goto(page)
            wait_rows(page)
            page.locator("[data-test='notif-select-toggle']").click()
            page.wait_for_timeout(400)
            page.locator("[data-test='notif-select-all']").click()
            page.wait_for_timeout(400)
            chk("全选后 3 条全被勾选", page.locator("[data-test='notif-checkbox'][data-selected='1']").count() == 3)
            page.locator("[data-test='notif-select-all']").click()
            page.wait_for_timeout(400)
            chk("取消全选后 0 条被勾选", page.locator("[data-test='notif-checkbox'][data-selected='1']").count() == 0)

            # ---------- 8) 未读视图下批量已读 -> 条目离开列表 ----------
            goto(page, "?filter=unread")
            n = wait_rows(page)
            chk("未读视图剩 2 条（participate 已在上一步读掉）", n == 2, f"{n}")
            page.locator("[data-test='notif-select-toggle']").click()
            page.wait_for_timeout(400)
            page.locator("[data-test='notif-select-all']").click()
            page.wait_for_timeout(400)
            page.locator("[data-test='notif-bulk-read']").click()
            page.wait_for_timeout(1200)
            chk("未读视图批量已读后列表清空", rows(page).count() == 0, f"{rows(page).count()}")
            chk("未读视图批量已读后数据库未读归零", unread_in_db(a["uid"]) == 0, f"{unread_in_db(a['uid'])}")

            # ---------- 9) 全部标为已读兜底 ----------
            goto(page)
            wait_rows(page)
            chk("回到全部视图仍有 3 条", rows(page).count() == 3, f"{rows(page).count()}")
            chk("已全部读完后不显示未读数", "全部已读" in page.locator("body").inner_text())

            browser.close()
    finally:
        cleanup_project(pid, (a["uid"], b["uid"], c["uid"]))

    finish()


if __name__ == "__main__":
    main()
