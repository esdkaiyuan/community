# -*- coding: utf-8 -*-
"""主页「查看全部」→ 广场人物筛选视图 —— 端到端验证

在**仓库根目录**执行：
    "C:\\Users\\28916\\AppData\\Local\\Programs\\Python\\Python313\\python.exe" scripts/verify_view_all.py

覆盖：
- 后端：GET /projects?creatorId= / ?participantId= 的集合语义（精确命中、不混入、参与不含自己发起的）、
  与 tag / sort=trending / sort=participants 叠加、不存在的用户返回空列表（不报错）、GET /users/:id 404
- 前端：主页两块列表「查看全部」（只在被截断时出现、括号计数用服务端真值）→ 带参跳广场 →
  banner 说清「在看谁」+ 清除筛选 + 回 TA 的主页 → 空状态（TA 没项目 / 用户不存在）
"""
from playwright.sync_api import sync_playwright

from _verify_common import (
    FRONT,
    api,
    api_status,
    attach,
    check,
    cleanup_project,
    cleanup_users,
    console_errors,
    create_project,
    finish,
    inject_login,
    register,
)

# 模块级：任何一步失败（含注册限流 429）都能在顶层 finally 里兜住
PIDS = []
UIDS = []


def main():
    owner = register("vwa")
    UIDS.append(owner["uid"])
    other = register("vwb")
    UIDS.append(other["uid"])
    print("临时用户:", owner["uid"], owner["username"], "|", other["uid"], other["username"])

    # 主页预览 6 条：各造 7 条才能触发「查看全部」
    owner_pids = [create_project(owner["token"], f"人物筛选-我的作品{i}", 1) for i in range(7)]
    PIDS.extend(owner_pids)
    other_pids = [create_project(other["token"], f"人物筛选-别人的作品{i}", 2) for i in range(7)]
    PIDS.extend(other_pids)

    # owner 参与 other 的全部项目（参与接口无请求体，必须显式 POST）
    for pid in other_pids:
        api(f"/projects/{pid}/participate", {}, token=owner["token"], method="POST")

    # owner 的前 3 条打上同一枚标签，用来验「人物筛选 + 标签筛选」叠加
    tag = f"vwt{owner['username'][-6:]}"
    for pid in owner_pids[:3]:
        api(f"/projects/{pid}", {"tags": [tag]}, token=owner["token"], method="PUT")

    # ---------- 后端：creatorId ----------
    res = api(f"/projects?creatorId={owner['uid']}&pageSize=50")["data"]
    ids = {p["id"] for p in res["projects"]}
    check("creatorId 精确返回 TA 发布的 7 个", ids == set(owner_pids))
    check("creatorId 不混入别人的项目", not (ids & set(other_pids)))
    check("creatorId 的 total 与条数一致", res["total"] == 7)

    # ---------- 后端：participantId ----------
    res = api(f"/projects?participantId={owner['uid']}&pageSize=50")["data"]
    ids = {p["id"] for p in res["projects"]}
    check("participantId 返回 TA 参与的 7 个", ids == set(other_pids))
    check("participantId 不含 TA 自己发起的", not (ids & set(owner_pids)))
    check("participantId 的 total 与条数一致", res["total"] == 7)

    # ---------- 后端：与其它筛选 / 排序叠加 ----------
    res = api(f"/projects?creatorId={owner['uid']}&tag={tag}&pageSize=50")["data"]
    check("人物筛选可与标签筛选叠加", res["total"] == 3)

    res = api(f"/projects?creatorId={owner['uid']}&sort=trending&pageSize=50")["data"]
    check("人物筛选可与 sort=trending 叠加", len(res["projects"]) == 7 and all("trendScore" in p for p in res["projects"]))

    res = api(f"/projects?participantId={owner['uid']}&sort=participants&pageSize=50")["data"]
    check("人物筛选可与 sort=participants 叠加", {p["id"] for p in res["projects"]} == set(other_pids))

    res = api(f"/projects?creatorId={owner['uid']}&participantId={owner['uid']}&pageSize=50")["data"]
    check("两个参数同时给按交集处理（自己发的不算「参与自己」）", res["total"] == 0)

    # ---------- 后端：不存在的用户 ----------
    res = api("/projects?creatorId=99999999&pageSize=50")["data"]
    check("不存在的 creatorId 返回空列表而不是报错", res["total"] == 0 and res["projects"] == [])
    status, _ = api_status("/users/99999999")
    check("不存在的用户主页 404（前端据此显示空状态）", status == 404)

    # ---------- 前端 ----------
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = attach(browser.new_page(viewport={"width": 1360, "height": 950}, device_scale_factor=2))
        inject_login(page, owner["token"], owner["user"])

        # 主页：两块列表都被截断 -> 两个「查看全部」都出现，计数是服务端真值
        page.goto(f"{FRONT}/user/{owner['uid']}", wait_until="networkidle")
        page.wait_for_timeout(1600)
        check("被截断时出现「查看全部」（发布）", page.locator("[data-test='view-all-created']").count() == 1)
        check("被截断时出现「查看全部」（参与）", page.locator("[data-test='view-all-joined']").count() == 1)
        check("发布数括号用服务端真值 7", page.locator("[data-test='created-count']").inner_text().strip() == "（7）")
        check("参与数括号用服务端真值 7", page.locator("[data-test='joined-count']").inner_text().strip() == "（7）")

        # 点「查看全部」（发布）-> 广场 creatorId 视图
        # ⚠️ 不用 wait_for_url：glob 里的 `?` 是单字符通配符，会被 URL 里的 `?` 搞乱
        page.locator("[data-test='view-all-created']").click()
        page.wait_for_timeout(1600)
        check("跳到广场并带上 creatorId", f"creatorId={owner['uid']}" in page.url)
        check("人物筛选时 Hero 让位（不再展示首页大标题）", page.get_by_text("让好创意落地生根").count() == 0)
        check("广场出现人物筛选 banner", page.locator("[data-test='person-banner']").count() == 1)
        title = page.locator("[data-test='person-title']").inner_text().strip()
        check("banner 说清在看谁的作品", owner["username"] in title and "发布的项目" in title)
        sub = page.locator("[data-test='person-sub']").inner_text().strip()
        check("banner 副标题报出总数", "7" in sub)
        check("只渲染 TA 的 7 张卡", page.locator("[data-test='projects-grid'] article").count() == 7)
        hrefs = page.locator("[data-test='projects-grid'] [data-test='card-link']").evaluate_all(
            "els => els.map(e => e.getAttribute('href'))"
        )
        href_pids = {int(h.rstrip("/").split("/")[-1]) for h in hrefs if h}
        check("列表里没有别人的项目", bool(href_pids) and not (href_pids & set(other_pids)))

        # banner 上的「查看 TA 的主页」
        page.locator("[data-test='person-profile']").click()
        page.wait_for_url(f"**/user/{owner['uid']}", timeout=6000)
        check("banner 可回到 TA 的主页", page.url.endswith(f"/user/{owner['uid']}"))

        # 清除筛选 -> 回到全量广场
        page.goto(f"{FRONT}/?creatorId={owner['uid']}", wait_until="networkidle")
        page.wait_for_timeout(1400)
        page.locator("[data-test='clear-person']").click()
        page.wait_for_timeout(1200)
        check("清除筛选后 banner 消失", page.locator("[data-test='person-banner']").count() == 0)
        check("清除筛选后 URL 不再带 creatorId", "creatorId=" not in page.url)
        check("清除筛选后 Hero 回来", page.get_by_text("让好创意落地生根").count() == 1)

        # participantId 视图：文案要说明口径，且不含自己发起的项目
        page.goto(f"{FRONT}/?participantId={owner['uid']}", wait_until="networkidle")
        page.wait_for_timeout(1500)
        title = page.locator("[data-test='person-title']").inner_text().strip()
        check("参与视图横幅文案是「参与的共创」", owner["username"] in title and "参与的共创" in title)
        sub = page.locator("[data-test='person-sub']").inner_text().strip()
        check("参与视图说明不含自己发起的项目", "不含 TA 自己发起的" in sub)
        check("参与视图渲染 7 张卡", page.locator("[data-test='projects-grid'] article").count() == 7)
        join_hrefs = page.locator("[data-test='projects-grid'] [data-test='card-link']").evaluate_all(
            "els => els.map(e => e.getAttribute('href'))"
        )
        join_pids = {int(h.rstrip("/").split("/")[-1]) for h in join_hrefs if h}
        check("参与视图不含 TA 自己发起的项目", bool(join_pids) and not (join_pids & set(owner_pids)))

        # 人物筛选下切换排序：URL 同时保留人物与排序
        page.get_by_role("button", name="本周热门").click()
        page.wait_for_timeout(1200)
        check("切换排序时保留人物筛选", f"participantId={owner['uid']}" in page.url and "sort=trending" in page.url)
        check("排序后 banner 仍在", page.locator("[data-test='person-banner']").count() == 1)
        check("排序后仍只显示 TA 参与的项目", page.locator("[data-test='projects-grid'] article").count() == 7)

        # 用户不存在：列表空 + banner 不给「查看 TA 的主页」（有条预期 404 网络日志，稍后剔除）
        mark = len(console_errors)
        page.goto(f"{FRONT}/?creatorId=99999999", wait_until="networkidle")
        page.wait_for_timeout(1500)
        check("不存在的用户走专属空状态", "找不到这位共创者" in page.content())
        check("用户不存在时不显示「查看 TA 的主页」", page.locator("[data-test='person-profile']").count() == 0)
        page.get_by_role("button", name="看看全部项目").click()
        page.wait_for_timeout(1000)
        check("空状态里的按钮能清除筛选", page.locator("[data-test='person-banner']").count() == 0)
        for err in console_errors[mark:]:
            if "404" in err:
                console_errors.remove(err)

        # 截图（先滚动到 banner 再截视口，避免 v-reveal 未到位的空白卡片）
        page.goto(f"{FRONT}/?creatorId={owner['uid']}", wait_until="networkidle")
        page.wait_for_timeout(1800)
        page.locator("[data-test='person-banner']").scroll_into_view_if_needed()
        page.wait_for_timeout(1600)
        page.screenshot(path="docs/screenshots/view-all-creator-light.png")
        page.emulate_media(color_scheme="dark")
        page.wait_for_timeout(1000)
        page.screenshot(path="docs/screenshots/view-all-creator-dark.png")

        browser.close()


if __name__ == "__main__":
    try:
        main()
    finally:
        for pid in PIDS:
            cleanup_project(pid)
        cleanup_users(UIDS)
        print("已清理临时项目与用户")
    finish()
