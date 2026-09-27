# -*- coding: utf-8 -*-
"""公开创作者主页 —— 端到端验证

在**仓库根目录**执行：
    "C:\\Users\\28916\\AppData\\Local\\Programs\\Python\\Python313\\python.exe" scripts/verify_user_profile.py

覆盖：
- 后端：GET /users/:id 公开可读、不含 email、统计口径（发布数 / 参与数不含自己发起的 / 获赞）、
  404 分支；GET /projects?participantId= 只回「作为成员参与」的项目，且与「只看收藏」可叠加取交集；
  ⚠️ GET /users/me 不能被 /users/:id 抢走（路由顺序）
- 前端：广场卡片创作者名、详情页发起人、共创伙伴名单都能点进主页；主页两块列表正确；
  不存在的用户走空状态；自己看自己出现「编辑我的资料」入口
"""
from playwright.sync_api import sync_playwright

from _verify_common import (
    FRONT,
    api,
    api_status,
    attach,
    check,
    cleanup_project,
    console_errors,
    cleanup_users,
    create_project,
    finish,
    inject_login,
    register,
)


def main():
    owner = register("upA")
    guest = register("upB")
    print("临时用户:", owner["uid"], guest["uid"])

    pids = []
    try:
        p_owner = create_project(owner["token"], f"主页主人的作品{owner['username']}", 1)
        p_guest = create_project(guest["token"], f"旁观者的作品{guest['username']}", 2)
        pids = [p_owner, p_guest]

        # 旁观者参与「主人的作品」：这是 TA 唯一一条「非自己发起」的参与记录
        # 注意：api() 不带 data 时默认 GET，POST 动作要显式 method
        api(f"/projects/{p_owner}/participate", token=guest["token"], method="POST")
        # 顺手收藏，用来验 participantId 与「只看收藏」的交集
        api(f"/projects/{p_owner}/favorite", token=guest["token"], method="POST")

        # ---------- 后端：公开主页 ----------
        body = api(f"/users/{owner['uid']}")
        data = body["data"]
        check("公开主页可读", data["user"]["id"] == owner["uid"])
        check("公开主页不含 email（只给 /me 返回）", "email" not in body.__str__())
        check("公开主页带用户名与加入时间", bool(data["user"]["username"]) and bool(data["user"]["joinedAt"]))
        check("发布数统计正确", data["stats"]["projectCount"] == 1)
        check("未参与别人项目时参与数为 0", data["stats"]["joinedCount"] == 0)
        check("统计字段齐全", set(data["stats"]) == {"projectCount", "joinedCount", "likeReceived"})

        # 未登录也能看（公开接口）
        status, _ = api_status(f"/users/{owner['uid']}")
        check("未登录可访问公开主页", status == 200)

        guest_data = api(f"/users/{guest['uid']}")["data"]
        check("参与数不含自己发起的项目", guest_data["stats"]["joinedCount"] == 1)

        status, body404 = api_status("/users/999999")
        check("不存在的用户返回 404", status == 404)
        check("404 给出可读提示", body404.get("message") == "用户不存在")

        # ⚠️ 路由顺序：/users/:id 必须排在 /users/me 之后
        me = api("/users/me", token=owner["token"])["data"]
        check("GET /users/me 没被 /users/:id 抢走", me["username"] == owner["username"])

        # ---------- 后端：参与过的项目 ----------
        joined = api(f"/projects?participantId={guest['uid']}")["data"]
        check("participantId 只回参与过的项目", [p["id"] for p in joined["projects"]] == [p_owner])
        check("participantId 不含自己发起的项目", p_guest not in [p["id"] for p in joined["projects"]])
        check("主人的参与列表为空（只发起未参与）", api(f"/projects?participantId={owner['uid']}")["data"]["total"] == 0)
        check("不存在的用户参与列表为空", api("/projects?participantId=999999")["data"]["total"] == 0)

        both = api(f"/projects?participantId={guest['uid']}&favorited=1", token=guest["token"])["data"]
        check("participantId 与「只看收藏」取交集", [p["id"] for p in both["projects"]] == [p_owner])
        empty = api(f"/projects?participantId={owner['uid']}&favorited=1", token=owner["token"])["data"]
        check("交集为空时短路返回而不是报错", empty["projects"] == [] and empty["total"] == 0)

        # ---------- 前端 ----------
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = attach(browser.new_page(viewport={"width": 1280, "height": 950}, device_scale_factor=2))

            # 广场卡片上的创作者名 -> 主页
            page.goto(f"{FRONT}/", wait_until="networkidle")
            page.wait_for_timeout(1500)
            creator = page.locator("[data-test='card-creator']").first
            creator.scroll_into_view_if_needed()
            check("广场卡片有创作者入口", creator.count() == 1)
            # 卡片 inner_text 以头像首字母开头，断言用「包含」而不是全等
            creator_text = creator.inner_text().strip()
            creator.click()
            page.wait_for_url("**/user/*", timeout=6000)
            check("点创作者名进到 TA 的主页", "/user/" in page.url)
            page.wait_for_selector("[data-test='user-profile']", timeout=6000)
            name = page.locator("[data-test='user-name']").inner_text().strip()
            check("主页名字与点击的那位一致", name in creator_text)

            # 详情页发起人 -> 主页 -> 两块列表
            page.goto(f"{FRONT}/project/{p_owner}", wait_until="networkidle")
            page.wait_for_timeout(1200)
            page.locator("[data-test='detail-creator-home']").click()
            page.wait_for_url(f"**/user/{owner['uid']}", timeout=6000)
            check("详情页「看看 TA 的其他项目」直达主页", page.url.endswith(f"/user/{owner['uid']}"))
            page.wait_for_timeout(1200)
            check("TA 发布的项目渲染出 1 张卡", page.locator("[data-test='user-created'] article").count() == 1)
            check("TA 未参与别人项目时参与区为空", page.locator("[data-test='user-joined']").count() == 0)

            # 旁观者：参与区应出现那条参与记录
            page.goto(f"{FRONT}/user/{guest['uid']}", wait_until="networkidle")
            page.wait_for_timeout(1600)
            check("旁观者主页参与区有 1 张卡", page.locator("[data-test='user-joined'] article").count() == 1)
            check("发布区与参与区不重复", page.locator("[data-test='user-created'] article").count() == 1)

            # 共创伙伴名单里的名字也可点
            page.goto(f"{FRONT}/project/{p_owner}", wait_until="networkidle")
            page.wait_for_timeout(1200)
            page.locator("[data-test='open-participants']").click()
            page.wait_for_selector("[data-test='participants-modal']", timeout=6000)
            page.wait_for_timeout(900)
            names = page.locator("[data-test='participant-name']")
            check("共创伙伴名单里每个人名都是链接", names.count() >= 2)

            # 不存在的用户走空状态（这一步会故意打出一条 404 网络日志，属预期，剔除后再统一判定）
            mark = len(console_errors)
            page.goto(f"{FRONT}/user/999999", wait_until="networkidle")
            page.wait_for_timeout(1200)
            check("不存在的用户显示空状态", "找不到这位共创者" in page.content())
            for err in console_errors[mark:]:
                if "404" in err:
                    console_errors.remove(err)

            # 自己看自己：出现「编辑我的资料」
            inject_login(page, owner["token"], owner["user"])
            page.goto(f"{FRONT}/user/{owner['uid']}", wait_until="networkidle")
            page.wait_for_timeout(1600)
            check("自己的主页出现编辑资料入口", page.locator("[data-test='user-edit-self']").count() == 1)
            page.locator("[data-test='user-edit-self']").click()
            page.wait_for_url("**/profile", timeout=6000)
            check("点编辑资料回到个人中心", page.url.endswith("/profile"))

            # 截图
            page.goto(f"{FRONT}/user/{guest['uid']}", wait_until="networkidle")
            page.wait_for_timeout(1600)
            page.screenshot(path="docs/screenshots/user-profile-light.png")
            page.emulate_media(color_scheme="dark")
            page.wait_for_timeout(900)
            page.screenshot(path="docs/screenshots/user-profile-dark.png")

            browser.close()
    finally:
        for pid in pids:
            cleanup_project(pid)
        cleanup_users([owner["uid"], guest["uid"]])
        print("已清理临时项目与用户")

    finish()


if __name__ == "__main__":
    main()
