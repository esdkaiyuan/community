# -*- coding: utf-8 -*-
"""验证评论深链（?comment=<id>）：通知 / 「我参与的讨论」直达那一条评论

覆盖：
- API：定位页号（分页边界）、回复按父级定位、pageSize 影响页号、评论不存在 404、
  跨项目 404、通知列表带 commentId
- 前端：跨页深链会先翻到那一页再滚动高亮、回复深链、通知点击直达、
  个人中心「我参与的讨论」深链、失效 id 只提示不崩
"""
import sys
import time

from playwright.sync_api import sync_playwright

sys.path.insert(0, "scripts")
from _verify_common import (  # noqa: E402
    FRONT,
    api,
    api_status,
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

TS = str(int(time.time()))[-5:]
PAGE_SIZE = 10  # 与 CommentSection 的 PAGE_SIZE 保持一致

PIDS = []
UIDS = []


def locate(pid, comment_id, page_size=None):
    q = f"/projects/{pid}/comments/locate?commentId={comment_id}"
    if page_size:
        q += f"&pageSize={page_size}"
    return api(q)["data"]


def main():
    owner = register("dlOwn")
    UIDS.append(owner["uid"])
    guest = register("dlGst")
    UIDS.append(guest["uid"])

    print("=== API ===")

    # p1：12 条根评论，用来验证分页边界（最新的 10 条在第 1 页，最早的 2 条在第 2 页）
    p1 = create_project(owner["token"], f"深链分页{TS}")
    PIDS.append(p1)
    ids = []
    for i in range(12):
        ids.append(comment(guest["token"], p1, f"第{i + 1}条评论{TS}")["id"])
    oldest, newest = ids[0], ids[-1]

    loc_old = locate(p1, oldest)
    loc_new = locate(p1, newest)
    check("最早的评论落在第 2 页（每页 10 条）", loc_old["page"] == 2)
    check("最新的评论落在第 1 页", loc_new["page"] == 1)
    check("根评论的 parentId 为空、rootId 指向自己", loc_old["parentId"] is None and loc_old["rootId"] == oldest)
    check("定位结果带回评论自身 id", loc_old["commentId"] == oldest)
    check("pageSize 影响页号（每页 20 条时最早那条在第 1 页）", locate(p1, oldest, 20)["page"] == 1)

    # 回复：挂在最早的评论下，定位结果应指向父级所在的页
    reply = comment(guest["token"], p1, f"回复最早那条{TS}", parent_id=oldest)
    loc_reply = locate(p1, reply["id"])
    check("回复按父级位置定位（同样第 2 页）", loc_reply["page"] == 2)
    check("回复的定位结果带 parentId", loc_reply["parentId"] == oldest)
    check("回复的 rootId 是父级而不是自己", loc_reply["rootId"] == oldest)

    status, body = api_status(f"/projects/{p1}/comments/locate?commentId=999999")
    check("不存在的评论返回 404", status == 404)
    check("不存在的评论给出可读提示", body.get("message") == "评论不存在")

    # 跨项目：另一项目的评论 id 不能在本项目定位到
    p2 = create_project(owner["token"], f"深链通知{TS}")
    PIDS.append(p2)
    only = comment(guest["token"], p2, f"用于通知的评论{TS}")
    st2, _ = api_status(f"/projects/{p1}/comments/locate?commentId={only['id']}")
    check("跨项目的评论 id 定位不到（404）", st2 == 404)

    # 通知带上 commentId，前端才有得可跳
    notif = api("/notifications?pageSize=50", token=owner["token"])["data"]["notifications"]
    hit = [n for n in notif if n.get("project", {}).get("id") == p2]
    check("评论通知带上了 commentId", hit and hit[0]["commentId"] == only["id"])
    check("参与类通知的 commentId 为 null", all(
        n.get("commentId") is None for n in notif if n["type"] == "participate"
    ))

    print("=== 前端 ===")
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = attach(browser.new_page())
        inject_login(page, owner["token"], owner["user"])

        # 1) 跨页深链：最早的评论在第 2 页，深链必须把那一页加载出来
        page.goto(f"{FRONT}/project/{p1}?comment={oldest}", wait_until="networkidle")
        page.wait_for_selector(f"#comment-{oldest}", timeout=8000)
        # 高亮只亮 2.4s，等太久截图里就只剩淡出后的痕迹了
        page.wait_for_timeout(900)
        check("跨页深链把目标评论加载出来了", page.locator(f"#comment-{oldest}").count() == 1)
        check(
            "目标评论滚动进了视口",
            page.evaluate(
                "(id) => { const r = document.getElementById(id).getBoundingClientRect();"
                "return r.top >= 0 && r.bottom <= window.innerHeight }",
                f"comment-{oldest}",
            ),
        )
        check(
            "目标评论处于高亮状态",
            "comment-flash" in (page.locator(f"#comment-{oldest}").get_attribute("class") or ""),
        )
        # class 挂上了还不够，确认动画真的在跑（全局样式无 hash 后缀）
        check(
            "高亮动画生效（computed animationName）",
            "comment-flash" in page.locator(f"#comment-{oldest}").evaluate("el => getComputedStyle(el).animationName"),
        )
        page.screenshot(path="docs/screenshots/comment-deeplink-light.png")

        # 2) 回复深链
        page.goto(f"{FRONT}/project/{p1}?comment={reply['id']}", wait_until="networkidle")
        page.wait_for_selector(f"#comment-{reply['id']}", timeout=8000)
        page.wait_for_timeout(1200)
        check("回复也能被深链命中并高亮", "comment-flash" in (
            page.locator(f"#comment-{reply['id']}").get_attribute("class") or ""
        ))

        # 3) 通知点击直达：p2 只有一条评论通知
        page.goto(f"{FRONT}/notifications", wait_until="networkidle")
        page.wait_for_selector("[data-test='notif-row']", timeout=8000)
        rows = page.locator("[data-test='notif-row']")
        target_row = rows.filter(has_text="用于通知的评论").first
        check("通知列表里能看到那条评论通知", target_row.count() == 1)
        target_row.click()
        page.wait_for_url("**/project/**", timeout=8000)
        page.wait_for_timeout(1800)
        check("点通知后 URL 带上了 comment 参数", f"comment={only['id']}" in page.url)
        check(
            "点通知后直接高亮到那条评论",
            "comment-flash" in (page.locator(f"#comment-{only['id']}").get_attribute("class") or ""),
        )

        # 4) 个人中心「我参与的讨论」深链
        mine = comment(owner["token"], p1, f"我自己的评论{TS}")
        page.goto(f"{FRONT}/profile", wait_until="networkidle")
        page.wait_for_selector("[data-test='profile-discussion']", timeout=8000)
        page.locator("[data-test='profile-discussion']").first.click()
        page.wait_for_url("**/project/**", timeout=8000)
        page.wait_for_timeout(1200)
        check("点「我参与的讨论」直达对应评论", f"comment={mine['id']}" in page.url)

        # 5) 失效的 comment id：提示一句，页面照常可用（404 网络日志是预期的）
        mark = len(console_errors)
        page.goto(f"{FRONT}/project/{p1}?comment=999999", wait_until="networkidle")
        page.wait_for_timeout(1500)
        check("失效 id 仍正常渲染评论列表", page.locator("[data-test='comment-item']").count() > 0)
        check("失效 id 给出提示", "这条评论已经不在了" in page.content())
        for e in list(console_errors[mark:]):
            if "404" in e:
                console_errors.remove(e)

        page.emulate_media(color_scheme="dark")
        page.goto(f"{FRONT}/project/{p1}?comment={newest}", wait_until="networkidle")
        page.wait_for_selector(f"#comment-{newest}", timeout=8000)
        page.wait_for_timeout(900)
        page.screenshot(path="docs/screenshots/comment-deeplink-dark.png")

        browser.close()


if __name__ == "__main__":
    try:
        main()
    finally:
        for p in PIDS:
            cleanup_project(p)
        if UIDS:
            cleanup_users(UIDS)
    finish()
