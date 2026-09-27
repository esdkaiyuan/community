# -*- coding: utf-8 -*-
"""验证「本周热门」排序（sort=trending）与卡片「本周 N」徽标

覆盖：
- API：近 7 天活跃度打分（参与 ×3 + 评论 ×2 + 点赞 ×1）、窗口外的旧互动不计入、
  发起人自己的参与行不计入、其它排序不带 trendScore、非法 sort 退化、未登录可用
- 前端：排序项可点、口径说明文案、卡片徽标数值与 API 一致、切走排序后徽标消失

结构注意：注册接口有 30 次/15 分钟的限流，一旦中途 429 抛异常，
注册必须也处在清理保护之内 —— 所以造数与清理都放在模块级 PIDS/UIDS + 顶层 finally，
不要写在 main() 的 try 里（注册在 try 之前发生时 finally 兜不住，会漏删用户）。
"""
import sys
import time

from playwright.sync_api import sync_playwright

sys.path.insert(0, "scripts")
from _verify_common import (  # noqa: E402
    FRONT,
    api,
    attach,
    check,
    cleanup_project,
    cleanup_users,
    comment,
    create_project,
    finish,
    inject_login,
    register,
    sql,
)

TS = str(int(time.time()))[-5:]
OLD_DAYS = 20  # 远在 7 天窗口之外

# 模块级，让顶层 finally 能兜住任何一步的失败
PIDS = []
UIDS = []


def backdate(pid):
    """把该项目的点赞 / 评论时间戳推到窗口之外（累计计数不动，只挪时间）"""
    sql(f"UPDATE project_likes SET created_at = DATE_SUB(NOW(), INTERVAL {OLD_DAYS} DAY) WHERE project_id = {pid};")
    sql(f"UPDATE project_comments SET created_at = DATE_SUB(NOW(), INTERVAL {OLD_DAYS} DAY) WHERE project_id = {pid};")


def main():
    owner = register("trOwn")
    UIDS.append(owner["uid"])
    u1 = register("trU1")
    UIDS.append(u1["uid"])
    u2 = register("trU2")
    UIDS.append(u2["uid"])
    u3 = register("trU3")
    UIDS.append(u3["uid"])

    print("=== API ===")

    # A：近期的 2 个赞 + 1 条评论 -> 2*1 + 1*2 = 4
    p_a = create_project(owner["token"], f"近期活跃{TS}", 1, ["近期"])
    # B：3 个赞 + 1 条评论，但全部发生在 20 天前 -> 窗口内 0 分；累计 like_count 最高
    p_b = create_project(owner["token"], f"旧日辉煌{TS}", 1, ["往昔"])
    # C：近期 1 位新伙伴加入 -> 1*3 = 3（发起人自己那一行不算）
    p_c = create_project(owner["token"], f"本周新伙伴{TS}", 1, ["新伙伴"])
    PIDS.extend([p_a, p_b, p_c])

    api(f"/projects/{p_a}/like", token=u1["token"], method="POST")
    api(f"/projects/{p_a}/like", token=u2["token"], method="POST")
    comment(u1["token"], p_a, f"近期评论{TS}")

    api(f"/projects/{p_b}/like", token=u1["token"], method="POST")
    api(f"/projects/{p_b}/like", token=u2["token"], method="POST")
    api(f"/projects/{p_b}/like", token=u3["token"], method="POST")
    comment(u1["token"], p_b, f"往昔评论{TS}")
    backdate(p_b)

    api(f"/projects/{p_c}/participate", {}, token=u1["token"], method="POST")

    recent = api("/projects?sort=trending&pageSize=50")["data"]["projects"]
    by_id = {p["id"]: p for p in recent}

    check("trending 排序返回了本次造的三个项目", all(i in by_id for i in PIDS))
    check("A 的得分为 4（2 赞 ×1 + 1 评论 ×2）", by_id[p_a]["trendScore"] == 4)
    check("C 的得分为 3（1 位新伙伴 ×3）", by_id[p_c]["trendScore"] == 3)
    check("B 的得分为 0（互动都在 7 天窗口之外）", by_id[p_b]["trendScore"] == 0)
    check("发起人自己计入参与人数（新建项目列表里就是 1，不是 0）", by_id[p_b]["participantCount"] == 1)
    check("C 有 1 位外部伙伴，参与人数为 2", by_id[p_c]["participantCount"] == 2)

    order = [p["id"] for p in recent]
    check("排序：A(4) 在 C(3) 之前", order.index(p_a) < order.index(p_c))
    check("排序：C(3) 在 B(0) 之前", order.index(p_c) < order.index(p_b))
    check("本周热门的第一名是近期活跃的项目", order[0] == p_a)

    # 旧互动仍然进了累计值：换个排序口径，B 应当翻盘
    hot = [p["id"] for p in api("/projects?sort=hot&pageSize=50")["data"]["projects"]]
    check("B 的累计点赞数是 3（旧赞进了 like_count）", by_id[p_b]["likeCount"] == 3)
    check("按累计热度排序时 B 反而在 A 之前（口径确实不同）", hot.index(p_b) < hot.index(p_a))

    latest = api("/projects?sort=latest&pageSize=50")["data"]["projects"]
    check("非 trending 排序不带 trendScore 字段", all("trendScore" not in p for p in latest))
    check("trending 排序每条都带 trendScore", all("trendScore" in p for p in recent))

    # 未登录可用 + 非法 sort 退化
    anon = api("/projects?sort=trending&pageSize=2")["data"]
    check("未登录也能按本周热门浏览", anon["total"] >= 3)
    check("pageSize 生效（只回 2 条）", len(anon["projects"]) == 2)
    weird = api("/projects?sort=not-a-sort&pageSize=5")["data"]["projects"]
    check("非法 sort 值静默退化为最新，不报错", len(weird) > 0 and "trendScore" not in weird[0])

    # 与其它筛选叠加
    tagged = api(f"/projects?sort=trending&tag={TS}")["data"]["projects"]
    check("本周热门与标签筛选叠加返回空结果也不报错", tagged == [])

    print("=== 前端 ===")
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = attach(browser.new_page())
        inject_login(page, owner["token"], owner["user"])

        page.goto(f"{FRONT}/?sort=trending", wait_until="networkidle")
        page.wait_for_selector("article", timeout=8000)
        page.wait_for_timeout(1500)

        check("URL 带着 sort=trending（可分享）", "sort=trending" in page.url)
        check("出现排序口径说明", page.locator("[data-test='trend-hint']").count() == 1)

        first = page.locator("article").first
        check("第一张卡是得分最高的项目", f"近期活跃{TS}" in first.inner_text())
        badge = first.locator("[data-test='card-trend']")
        check("第一张卡显示本周徽标", badge.count() == 1)
        check("徽标数值与 API 一致（本周 4）", "本周 4" in badge.inner_text())

        # 截图对准排序条与卡片网格，而不是页面顶部的 Hero
        page.locator("[data-test='trend-hint']").scroll_into_view_if_needed()
        page.wait_for_timeout(1600)
        page.screenshot(path="docs/screenshots/trending-light.png")

        # 切到「最新」：说明与徽标都应消失
        page.get_by_role("button", name="最新", exact=True).click()
        page.wait_for_timeout(1200)
        check("切到最新后说明文案消失", page.locator("[data-test='trend-hint']").count() == 0)
        check("切到最新后徽标消失", page.locator("[data-test='card-trend']").count() == 0)
        # 「最新」是默认排序，syncRoute 会把它从 URL 里省掉，保持地址干净
        check("切到最新后 URL 里不再带 sort（默认值不上地址）", "sort=" not in page.url)

        # 切回「本周热门」
        page.get_by_role("button", name="本周热门", exact=True).click()
        page.wait_for_timeout(1200)
        check("切回本周热门后徽标重现", page.locator("[data-test='card-trend']").count() > 0)

        page.emulate_media(color_scheme="dark")
        # 切排序触发了路由跳转，视口会回到页顶；深色截图同样对准排序条
        page.locator("[data-test='trend-hint']").scroll_into_view_if_needed()
        page.wait_for_timeout(1600)
        page.screenshot(path="docs/screenshots/trending-dark.png")

        browser.close()


if __name__ == "__main__":
    try:
        main()
    finally:
        # 注册 / 造数任何一步抛异常（限流 429、断言外的意外）都能清干净
        for p in PIDS:
            cleanup_project(p)
        if UIDS:
            cleanup_users(UIDS)
    finish()
