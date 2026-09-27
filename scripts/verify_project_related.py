# -*- coding: utf-8 -*-
"""相关项目推荐 + 个人中心卡片编辑入口 —— 端到端验证

在**仓库根目录**执行：
    "C:\\Users\\28916\\AppData\\Local\\Programs\\Python\\Python313\\python.exe" scripts/verify_project_related.py

覆盖：
- 后端打分：共同标签 x3 + 同分类 x2 + 跨发起人 +1，依据（relatedReason）随结果返回；
  排除自身、排除「无线索」的候选、错误 project 返回 404、limit 参数容错
- 前端：详情页推荐区渲染、首条是高相关项、点击可跳转、无线索时整块不渲染；
  个人中心「我发布的项目」卡片上的编辑入口可直达编辑页，广场卡片不出现该入口
"""
import time

from playwright.sync_api import sync_playwright

from _verify_common import (
    FRONT,
    api,
    api_status,
    attach,
    check,
    cleanup_project,
    cleanup_users,
    create_project,
    finish,
    inject_login,
    register,
)

# 本轮专用标签（不同于账号后缀，长度需 <= 12）
STAMP = str(int(time.time()))[-5:]
T1, T2, T3, T4 = f"R{STAMP}", f"S{STAMP}", f"X{STAMP}", f"Y{STAMP}"


def build_fixture(owner, other):
    """造一组刻意设计过的分数阶梯，返回 {name: pid}

    基准项目 base（owner，分类 1，标签 T1+T2）的预期排序：
      two_tags  7 = 共同标签 2x3 + 跨发起人 1        （其它分类，标签 T1+T2+T3）
      tag_cat   6 = 共同标签 1x3 + 同分类 2 + 跨发起人 1
      same_crea 5 = 共同标签 1x3 + 同分类 2 + 同一发起人 0
      only_cat  3 = 同分类 2 + 跨发起人 1
    另有一个「无线索」项目 stray（其它分类 + 独有标签），根本不该进候选池；
    lonely 连自己都没有标签、也没有同分类邻居，用来验「没有线索就不硬推」。
    """
    return {
        "base": create_project(owner["token"], f"基准项目{owner['username']}", 1, [T1, T2]),
        "two_tags": create_project(other["token"], f"双标签邻居{other['username']}", 2, [T1, T2, T3]),
        "tag_cat": create_project(other["token"], f"标签同分类{other['username']}", 1, [T1]),
        "same_crea": create_project(owner["token"], f"同发起人{owner['username']}", 1, [T1]),
        "only_cat": create_project(other["token"], f"仅同分类{other['username']}", 1, []),
        "stray": create_project(other["token"], f"无关项目{other['username']}", 5, [T4]),
        "lonely": create_project(owner["token"], f"无标签无同类{owner['username']}", 3, []),
    }


def related(pid, **params):
    query = "&".join(f"{k}={v}" for k, v in params.items())
    path = f"/projects/{pid}/related"
    return api(path if not query else f"{path}?{query}")["data"]


def main():
    owner = register("relA")
    other = register("relB")
    print("临时用户:", owner["uid"], other["uid"])

    f = build_fixture(owner, other)
    print("临时项目:", list(f.values()))

    try:
        # ---------- 后端：排序与排除规则 ----------
        default_list = related(f["base"])
        check("默认返回 3 条推荐", len(default_list) == 3)
        check(
            "按相关度排序：双标签 > 标签+同分类 > 同发起人的同分类",
            [p["id"] for p in default_list] == [f["two_tags"], f["tag_cat"], f["same_crea"]],
        )
        check("推荐结果不含项目自身", f["base"] not in [p["id"] for p in default_list])

        full = related(f["base"], limit=4)
        check(
            "limit=4 补齐到 4 条（含仅同分类项）",
            [p["id"] for p in full] == [f["two_tags"], f["tag_cat"], f["same_crea"], f["only_cat"]],
        )
        check("无共同标签也无同分类的项目不进推荐", f["stray"] not in [p["id"] for p in full])

        # ---------- 后端：推荐依据要能自证 ----------
        by_id = {p["id"]: p for p in full}
        check("每条推荐都带 relatedReason", all(p.get("relatedReason") for p in full))
        check(
            "共同标签原样返回",
            sorted(by_id[f["two_tags"]]["relatedReason"]["sharedTags"]) == sorted([T1, T2]),
        )
        check("双标签邻居不算同分类", by_id[f["two_tags"]]["relatedReason"]["sameCategory"] is False)
        check("第三项是同一发起人的作品", by_id[f["same_crea"]]["relatedReason"]["sameCreator"] is True)
        check("推荐项带齐卡片所需字段", "creator" in full[0] and "participantCount" in full[0])

        # ---------- 后端：参数容错与错误分支 ----------
        check("limit=1 只返回 1 条", len(related(f["base"], limit=1)) == 1)
        check("limit=0 回落到默认 3 条", len(related(f["base"], limit=0)) == 3)
        check("limit=abc 回落到默认 3 条", len(related(f["base"], limit="abc")) == 3)
        status, body = api_status(f"/projects/{f['base']}/related")
        check("推荐接口公开可读（未登录 200）", status == 200 and isinstance(body["data"], list))
        status, body = api_status("/projects/999999/related")
        check("不存在的项目返回 404", status == 404)
        check("404 给出可读提示", body.get("message") == "项目不存在")

        # 没有线索宁可什么都不推，也不拿无关结果凑数
        check("无标签且无同类的项目返回空推荐", related(f["lonely"]) == [])
        check("无关项目自身也推不出东西", related(f["stray"]) == [])

        # ---------- 前端 ----------
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = attach(browser.new_page(viewport={"width": 1280, "height": 950}, device_scale_factor=2))
            inject_login(page, owner["token"], owner["user"])

            page.goto(f"{FRONT}/project/{f['base']}", wait_until="networkidle")
            page.wait_for_timeout(1200)
            section = page.locator("[data-test='related-section']")
            section.scroll_into_view_if_needed()
            page.wait_for_timeout(1600)  # v-reveal 渐入 + 推荐请求落地
            check("详情页渲染出相关推荐区", section.count() == 1)
            check("推荐区默认 3 张卡", page.locator("[data-test='related-item']").count() == 3)

            first = page.locator("[data-test='related-item']").first
            check("首条推荐把推荐依据写在卡片上", T1 in first.inner_text())
            check("首条推荐指向最高分邻居", first.get_attribute("href") == f"/project/{f['two_tags']}")

            first.click()
            page.wait_for_url(f"**/project/{f['two_tags']}", timeout=6000)
            check("点推荐卡能跳到该项目", page.url.endswith(f"/project/{f['two_tags']}"))
            # 换项目后推荐区要跟着重拉（watch projectId）
            page.locator("[data-test='related-section']").scroll_into_view_if_needed()
            page.wait_for_timeout(1600)
            check(
                "跳到邻居后推荐区跟着换了内容",
                (page.locator("[data-test='related-item']").first.get_attribute("href") or "")
                != f"/project/{f['two_tags']}",
            )

            # 无线索的项目：整块不渲染
            page.goto(f"{FRONT}/project/{f['lonely']}", wait_until="networkidle")
            page.wait_for_timeout(1500)
            check("无线索时推荐区整块不出现", page.locator("[data-test='related-section']").count() == 0)

            # 个人中心：卡片上的编辑入口（原来要先进详情页）
            page.goto(f"{FRONT}/profile", wait_until="networkidle")
            page.wait_for_timeout(1600)
            my_card = page.locator("[data-test='profile-my-projects'] article").first
            my_card.scroll_into_view_if_needed()
            page.wait_for_timeout(700)
            check("我发布的项目卡片上有编辑入口", my_card.locator("[data-test='card-edit']").count() == 1)
            expected_title = my_card.locator("h3").inner_text().strip()
            my_card.locator("[data-test='card-edit']").click()
            page.wait_for_url("**/edit", timeout=6000)
            check("点编辑直达编辑页（省掉先进详情页的 2 跳）", "/edit" in page.url)
            page.wait_for_selector("[data-test='project-form']", timeout=6000)
            check(
                "编辑页标题回填正确",
                page.locator("#title").input_value().strip() == expected_title,
            )

            # 广场（公共列表）不该出现编辑入口
            page.goto(f"{FRONT}/", wait_until="networkidle")
            page.wait_for_timeout(1500)
            check("广场卡片不出现编辑入口", page.locator("[data-test='card-edit']").count() == 0)

            # 截图
            page.goto(f"{FRONT}/project/{f['base']}", wait_until="networkidle")
            page.locator("[data-test='related-section']").scroll_into_view_if_needed()
            page.wait_for_timeout(1600)
            page.screenshot(path="docs/screenshots/related-light.png")
            page.emulate_media(color_scheme="dark")
            page.wait_for_timeout(900)
            page.screenshot(path="docs/screenshots/related-dark.png")

            page.goto(f"{FRONT}/profile", wait_until="networkidle")
            page.wait_for_timeout(1600)
            page.emulate_media(color_scheme="dark")
            page.wait_for_timeout(700)
            page.screenshot(path="docs/screenshots/profile-card-edit-dark.png")
            page.emulate_media(color_scheme="light")
            page.wait_for_timeout(700)
            page.screenshot(path="docs/screenshots/profile-card-edit-light.png")

            browser.close()
    finally:
        for pid in f.values():
            cleanup_project(pid)
        cleanup_users([owner["uid"], other["uid"]])
        print("已清理临时项目与用户")

    finish()


if __name__ == "__main__":
    main()
