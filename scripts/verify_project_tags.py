# -*- coding: utf-8 -*-
"""标签导航验证

覆盖：
- API：按标签筛选（JSON_CONTAINS 精确匹配，互含子串不误命中）、搜索命中标签、
  热门标签聚合与排序、limit、tag 与分页组合、详情返回 tags
- 前端：详情页标签可点、卡片标签可点（不跳详情页）、热门标签入口与选中态、
  空状态、清除筛选、整卡 stretched link 仍可跳详情
运行：
    "C:\\Users\\28916\\AppData\\Local\\Programs\\Python\\Python313\\python.exe" scripts/verify_project_tags.py
"""
from urllib.parse import quote

from _verify_common import (
    FRONT,
    TS,
    api,
    attach,
    check,
    cleanup_project,
    cleanup_users,
    create_project,
    finish,
    register,
)

from playwright.sync_api import sync_playwright

SHOTS = "docs/screenshots"

TAG_SHARED = "开源"          # 与 TAG_SUB 互为子串，用来证明精确匹配
TAG_SUB = "开源硬件"
TAG_MINE = f"共创{TS}"       # 只有本次脚本会造出来，可安全断言总数
TAG_NOPE = f"没有这个标签{TS}"


def ids_for(**params):
    """按查询参数取项目 id 与总数"""
    qs = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
    data = api(f"/projects?{qs}")["data"]
    return [p["id"] for p in data["projects"]], data["total"]


def main():
    pids = []
    uids = []
    try:
        creator = register("tagcre")
        uids.append(creator["uid"])
        token = creator["token"]

        p1 = create_project(token, f"标签验证甲{TS}", tags=[TAG_SHARED, TAG_MINE])
        p2 = create_project(token, f"标签验证乙{TS}", tags=[TAG_SUB])
        p3 = create_project(token, f"标签验证丙{TS}", tags=[TAG_MINE])
        pids += [p1, p2, p3]

        # ---------- API ----------
        ids, total = ids_for(tag=TAG_MINE, pageSize=50)
        check("按标签筛选命中该标签的全部项目", sorted(ids) == sorted([p1, p3]) and total == 2)

        ids_sub, total_sub = ids_for(tag=TAG_SHARED, pageSize=50)
        check("精确匹配：只命中同名标签的项目", ids_sub == [p1] and total_sub == 1)
        check("子串不误命中：「开源」不匹配「开源硬件」", p2 not in ids_sub)

        _, total_none = ids_for(tag=TAG_NOPE, pageSize=50)
        check("不存在的标签返回 0 条", total_none == 0)

        ids_search, _ = ids_for(search=TAG_MINE, pageSize=50)
        check("搜索命中标签（唯一标签）", sorted(ids_search) == sorted([p1, p3]))
        ids_search_sub, _ = ids_for(search=TAG_SUB, pageSize=50)
        check("搜索命中仅存在于标签里的关键词", p2 in ids_search_sub)

        tags_res = api("/projects/tags")["data"]
        by_name = {t["name"]: t["count"] for t in tags_res}
        check("热门标签含本次造的唯一标签且计数正确", by_name.get(TAG_MINE) == 2)
        check("热门标签同时含两个互含子串的标签", by_name.get(TAG_SHARED) == 1 and by_name.get(TAG_SUB) == 1)
        counts = [t["count"] for t in tags_res]
        check("热门标签按项目数非递增", all(a >= b for a, b in zip(counts, counts[1:])))
        check("热门标签 limit 生效", len(api("/projects/tags?limit=1")["data"]) == 1)

        _, total_paged = ids_for(tag=TAG_MINE, pageSize=1, page=2)
        check("标签筛选与分页组合（total 不随页码变化）", total_paged == 2)

        detail = api(f"/projects/{p1}")["data"]
        check("详情返回完整标签数组", sorted(detail["tags"]) == sorted([TAG_SHARED, TAG_MINE]))

        # ---------- 前端 ----------
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = attach(browser.new_page(viewport={"width": 1440, "height": 960}))

            # 详情页标签可点
            page.goto(f"{FRONT}/project/{p1}", wait_until="networkidle")
            page.wait_for_timeout(1200)
            check("详情页渲染出全部标签入口", page.locator("[data-test='detail-tag']").count() == 2)
            page.screenshot(path=f"{SHOTS}/project-tags-detail.png")

            page.locator("[data-test='detail-tag']", has_text=TAG_MINE).first.click()
            page.wait_for_timeout(900)
            check("点详情页标签跳广场并带上 tag 参数", "tag=" in page.url and "/project/" not in page.url)
            check(
                "广场显示标签筛选标题",
                page.locator("h2", has_text=f"标签「{TAG_MINE}」下的项目").count() == 1,
            )
            check("筛选后只剩该标签的 2 个项目", page.locator("article").count() == 2)
            check(
                "热门标签行里该标签为选中态",
                page.locator("[data-test='popular-tags'] [aria-current='page']").count() == 1,
            )
            page.screenshot(path=f"{SHOTS}/project-tags-square-light.png")

            # 卡片上的标签也可点，且不跳详情页
            first_tag = page.locator("[data-test='card-tag']").first
            check("卡片上渲染出标签入口", page.locator("[data-test='card-tag']").count() >= 2)
            first_tag.click()
            page.wait_for_timeout(900)
            check("点卡片标签切换筛选而不是进详情页", "/project/" not in page.url and "tag=" in page.url)

            # 热门标签入口点回唯一标签
            chip = page.locator("[data-test='popular-tags'] .chip-link", has_text=TAG_MINE).first
            chip.click()
            page.wait_for_timeout(900)
            check("点热门标签胶囊进入对应筛选", quote(TAG_MINE) in page.url or TAG_MINE in page.url)

            page.emulate_media(color_scheme="dark")
            page.reload(wait_until="networkidle")
            page.wait_for_timeout(1200)
            check("深色模式下标签筛选仍然生效", page.locator("article").count() == 2)
            page.screenshot(path=f"{SHOTS}/project-tags-square-dark.png")
            page.emulate_media(color_scheme="light")

            # 清除筛选
            page.locator("[data-test='clear-tag']").click()
            page.wait_for_timeout(900)
            check("清除筛选后 URL 不再带 tag", "tag=" not in page.url)
            check("清除后恢复全量列表", page.locator("article").count() > 2)

            # 空状态
            page.goto(f"{FRONT}/?tag={quote(TAG_NOPE)}", wait_until="networkidle")
            page.wait_for_timeout(1000)
            check(
                "无结果标签给出专属空状态",
                page.get_by_text(f"还没有「{TAG_NOPE}」标签的项目").count() == 1,
            )
            page.screenshot(path=f"{SHOTS}/project-tags-empty.png")

            # 整卡点击（stretched link）仍然有效
            page.goto(f"{FRONT}/", wait_until="networkidle")
            page.wait_for_timeout(1400)
            page.locator("[data-test='card-link']").first.click()
            page.wait_for_timeout(1200)
            check("整卡点击仍能进入详情页（stretched link 生效）", "/project/" in page.url)

            browser.close()
    finally:
        for pid in pids:
            cleanup_project(pid)
        cleanup_users(uids)
        print("已清理临时项目:", pids)

    finish()


if __name__ == "__main__":
    main()
