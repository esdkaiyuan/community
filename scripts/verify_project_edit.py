# -*- coding: utf-8 -*-
"""项目编辑页验证

覆盖：
- API：标签归一化（去空白 / 去重 / 剥 emoji / 单标签截断 / 5 个上限）落库、
  清空标签、分类必选（400 而不是 500）、非作者 403、不存在 404、
  字段校验（标题/介绍过短）、编辑后详情与「按标签筛选」即时生效
- 前端：未登录跳登录、非作者看到拦截页、作者从详情页进编辑页、
  表单回填（标题 / 分类选中 / 已选标签）、发布页分类必选校验、
  快捷标签一键添加（已选的不重复出现、只被一个项目用过的标签不进候选）、
  提交后详情页标题与标签更新、编辑出的新标签进入广场热门标签行
运行：
    "C:\\Users\\28916\\AppData\\Local\\Programs\\Python\\Python313\\python.exe" scripts/verify_project_edit.py
"""
from urllib.parse import quote

from _verify_common import (
    FRONT,
    TS,
    api,
    api_status,
    attach,
    check,
    cleanup_project,
    cleanup_users,
    finish,
    inject_login,
    register,
    sql_one,
)

from playwright.sync_api import sync_playwright

SHOTS = "docs/screenshots"

DESC = "这是一条用于自动化验证的临时项目描述，写长一点以便通过 20 字下限。"
LONG_TAG = "这是一个非常长的标签名称需要被截断"
POP_TAG = f"热门候选{TS}"  # 被两个项目用过的标签，应当出现在快捷候选里
SOLO_TAG = f"单次标签{TS}"  # 只被一个项目用过，不该被当成推荐标签
KEEP_TAG = f"保留标签{TS}"
NEW_TITLE = f"改名后的项目{TS}"

base_body = lambda **kw: {
    "title": f"编辑验证项目{TS}",
    "description": DESC,
    "categoryId": 1,
    **kw,
}


def main():
    pids = []
    uids = []
    try:
        owner = register("editown")
        other = register("editothr")
        uids += [owner["uid"], other["uid"]]

        # ---------- API：标签归一化 ----------
        p1 = api("/projects", base_body(tags=[" 开源 ", "开源", "开源硬件", "", "🌱环保"]), token=owner["token"])["data"]
        pids.append(p1["id"])
        check(
            "创建时归一化标签：去空白 + 去重 + 剥 emoji",
            p1["tags"] == ["开源", "开源硬件", "环保"],
        )
        check(
            "标签确实落库为归一化后的 JSON",
            sql_one(f"SELECT tags FROM projects WHERE id = {p1['id']}") == '["开源","开源硬件","环保"]',
        )

        p2 = api("/projects", base_body(tags=[LONG_TAG, "a", "b", "c", "d", "e", "f"]), token=owner["token"])["data"]
        pids.append(p2["id"])
        check("单标签超过 12 字被截断", p2["tags"][0] == LONG_TAG[:12])
        check("标签数组最多保留 5 个", len(p2["tags"]) == 5)
        check("上限截断保留的是前 5 个", p2["tags"] == [LONG_TAG[:12], "a", "b", "c", "d"])

        # ---------- API：分类必选 ----------
        # 故意不带 categoryId（base_body 默认是带分类的，这里显式剔除）
        no_category = {k: v for k, v in base_body().items() if k != "categoryId"}
        status, body = api_status("/projects", no_category, token=owner["token"])
        check("创建不带分类返回 400 而不是 500", status == 400)
        check("创建不带分类给出可读提示", body.get("message") == "请选择项目分类")

        status, body = api_status("/projects", base_body(categoryId=999999), token=owner["token"])
        check("创建带不存在的分类返回 400", status == 400 and body.get("message") == "所选分类不存在")

        # ---------- API：编辑 ----------
        status, body = api_status(
            f"/projects/{p1['id']}",
            {"title": NEW_TITLE, "description": DESC, "categoryId": 2, "tags": [KEEP_TAG, POP_TAG]},
            token=owner["token"],
            method="PUT",
        )
        check("本人编辑项目成功", status == 200)
        updated = body["data"]
        check("编辑后标题与分类已更新", updated["title"] == NEW_TITLE and updated["categoryId"] == 2)
        check("编辑后标签已替换", sorted(updated["tags"]) == sorted([KEEP_TAG, POP_TAG]))

        detail = api(f"/projects/{p1['id']}")["data"]
        check("详情接口读到新标题", detail["title"] == NEW_TITLE)
        check("详情接口读到新标签", sorted(detail["tags"]) == sorted([KEEP_TAG, POP_TAG]))
        # 秒级比对：create 的内存 Date 带毫秒，DB 的 DATETIME 不存毫秒
        check("编辑不改变创建时间", detail["createdAt"][:19] == p1["createdAt"][:19])

        ids, total = (
            lambda d: ([p["id"] for p in d["projects"]], d["total"])
        )(api(f"/projects?tag={quote(POP_TAG)}&pageSize=50")["data"])
        check("编辑出的新标签立刻可用于标签导航", ids == [p1["id"]] and total == 1)

        # 校验分支
        status, body = api_status(f"/projects/{p1['id']}", {"title": "短"}, token=owner["token"], method="PUT")
        check("编辑时标题过短返回 400", status == 400 and body.get("message") == "标题至少 4 个字符")

        status, body = api_status(
            f"/projects/{p1['id']}", {"categoryId": None}, token=owner["token"], method="PUT"
        )
        check("编辑时清空分类返回 400", status == 400 and body.get("message") == "请选择项目分类")

        status, _ = api_status(
            f"/projects/{p1['id']}", {"title": NEW_TITLE}, token=other["token"], method="PUT"
        )
        check("非作者编辑返回 403", status == 403)

        status, _ = api_status("/projects/99999999", {"title": NEW_TITLE}, token=owner["token"], method="PUT")
        check("编辑不存在的项目返回 404", status == 404)

        # 清空标签
        cleared = api(
            f"/projects/{p1['id']}",
            {"tags": []},
            token=owner["token"],
            method="PUT",
        )["data"]
        check("传空数组可清空标签", cleared["tags"] == [])
        check("清空后落库为空 JSON 数组", sql_one(f"SELECT tags FROM projects WHERE id = {p1['id']}") == "[]")

        # 恢复成待验证状态；再用「别人的项目」把 POP_TAG 顶成真·热门标签（≥2 个项目在用）
        # 同时造一个只被一个项目用过的 SOLO_TAG，用来验证它不会被当成推荐标签
        api(f"/projects/{p1['id']}", {"tags": [KEEP_TAG, "开源"]}, token=owner["token"], method="PUT")
        for _ in range(2):
            p_other = api("/projects", base_body(tags=[POP_TAG]), token=other["token"])["data"]
            pids.append(p_other["id"])
        p_solo = api("/projects", base_body(tags=[SOLO_TAG]), token=other["token"])["data"]
        pids.append(p_solo["id"])

        popular = {t["name"]: t["count"] for t in api("/projects/tags")["data"]}
        check("热门标签里出现本次编辑出的标签", POP_TAG in popular)
        check("被两个项目使用的标签计数为 2", popular.get(POP_TAG) == 2)
        check("只被一个项目使用的标签计数为 1", popular.get(SOLO_TAG) == 1)

        # ---------- 前端 ----------
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = attach(browser.new_page(viewport={"width": 1440, "height": 960}))
            edit_url = f"{FRONT}/project/{p1['id']}/edit"

            # 未登录：requiresAuth 拦到登录页
            page.goto(edit_url, wait_until="networkidle")
            page.wait_for_timeout(600)
            check("未登录访问编辑页被拦到登录页", "/login" in page.url and "redirect" in page.url)

            # 非作者：拦截页
            inject_login(page, other["token"], other["user"])
            page.goto(edit_url, wait_until="networkidle")
            page.wait_for_timeout(1200)
            check("非作者看到「只有发起人可以编辑」", page.locator("[data-test='edit-forbidden']").count() == 1)
            check("非作者看不到编辑表单", page.locator("[data-test='project-form']").count() == 0)

            page.goto(f"{FRONT}/project/{p1['id']}", wait_until="networkidle")
            page.wait_for_timeout(1200)
            check("非作者详情页没有编辑入口", page.locator("[data-test='detail-edit']").count() == 0)

            # 作者：详情页入口 -> 编辑页
            inject_login(page, owner["token"], owner["user"])
            page.goto(f"{FRONT}/project/{p1['id']}", wait_until="networkidle")
            page.wait_for_timeout(1400)
            check("作者详情页出现编辑入口", page.locator("[data-test='detail-edit']").count() == 1)

            page.locator("[data-test='detail-edit']").click()
            page.wait_for_timeout(1500)
            check("点编辑入口进入编辑页", f"/project/{p1['id']}/edit" in page.url)
            check("编辑页渲染出表单", page.locator("[data-test='project-form']").count() == 1)
            check("表单回填原标题", page.locator("#title").input_value() == NEW_TITLE)
            check(
                "表单回填分类为选中态",
                page.locator("[data-test='category-option'][aria-pressed='true']").count() == 1,
            )
            check(
                "表单回填已选标签",
                page.locator("[data-test='selected-tag']").count() == 2,
            )
            check(
                "已选标签内容与后端一致",
                KEEP_TAG in page.locator("[data-test='selected-tag']").first.inner_text(),
            )
            page.screenshot(path=f"{SHOTS}/project-edit-form-light.png")

            # 快捷标签：已选的不重复出现，未选的点了就加上
            suggestions = page.locator("[data-test='tag-suggestions'] [data-test='tag-suggestion']")
            check("渲染出快捷标签候选", page.locator("[data-test='tag-suggestions']").count() == 1 and suggestions.count() > 0)
            check(
                "已选中的标签不再出现在候选里",
                all(
                    KEEP_TAG not in suggestions.nth(i).inner_text()
                    for i in range(suggestions.count())
                ),
            )
            pop_chip = suggestions.filter(has_text=POP_TAG).first
            check("候选里包含被两个项目用过的热门标签", pop_chip.count() == 1)
            check(
                "只被一个项目用过的标签不进候选（避免把随手标签当推荐）",
                suggestions.filter(has_text=SOLO_TAG).count() == 0,
            )
            pop_chip.click()
            page.wait_for_timeout(400)
            check("点候选标签即加入已选", page.locator("[data-test='selected-tag']").count() == 3)
            check(
                "加入后候选里不再重复该标签",
                suggestions.filter(has_text=POP_TAG).count() == 0,
            )

            # 提交编辑
            page.locator("#title").fill(NEW_TITLE)
            page.locator("[data-test='submit-project']").click()
            page.wait_for_timeout(2000)
            check("提交后跳回项目详情页", f"/project/{p1['id']}" in page.url and "/edit" not in page.url)
            check("详情页标题已是新值", page.locator("h1").first.inner_text().strip() == NEW_TITLE)
            check(
                "详情页渲染出刚添加的标签",
                page.locator("[data-test='detail-tag']", has_text=POP_TAG).count() == 1,
            )

            # 新标签进入广场热门标签行
            page.goto(f"{FRONT}/?tag={quote(POP_TAG)}", wait_until="networkidle")
            page.wait_for_timeout(1400)
            # 另外两个临时项目也带着这个标签，所以广场下应当正好有 3 个
            check("广场可按新标签筛选到编辑过的项目", page.locator("article").count() == 3)
            check("广场热门标签行出现该标签", page.locator("[data-test='popular-tags']").count() == 1)

            page.emulate_media(color_scheme="dark")
            page.reload(wait_until="networkidle")
            page.wait_for_timeout(1400)
            page.screenshot(path=f"{SHOTS}/project-edit-square-dark.png")
            page.emulate_media(color_scheme="light")

            # 发布页：分类必选的前端校验
            page.goto(f"{FRONT}/publish", wait_until="networkidle")
            page.wait_for_timeout(1400)
            check("发布页渲染出表单", page.locator("[data-test='project-form']").count() == 1)
            page.locator("[data-test='submit-project']").click()
            page.wait_for_timeout(600)
            check("空表单提交被前端拦下（未离开发布页）", "/publish" in page.url)
            check("给出分类必选提示", page.locator("[data-test='error-category']").count() == 1)
            check(
                "提示文案明确说清要选分类",
                "分类" in page.locator("[data-test='error-category']").inner_text(),
            )
            check("发布页也有快捷标签候选（冷启动有默认池）", page.locator("[data-test='tag-suggestions']").count() == 1)
            page.screenshot(path=f"{SHOTS}/project-edit-publish-light.png")

            browser.close()
    finally:
        for pid in pids:
            cleanup_project(pid)
        cleanup_users(uids)
        print("已清理临时项目:", pids)

    finish()


if __name__ == "__main__":
    main()
