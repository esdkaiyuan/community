# -*- coding: utf-8 -*-
"""「参与共创」通知发起人 验证

覆盖：
1) 有人参与 → 发起人收到 type=participate 通知（actor / project 指向正确，无评论预览）
2) 去重：同一人「退出 → 再加入」不重复通知（防止刷屏）
3) 不同参与者各产生一条
4) 自参与不通知（创建者重复参与被 409 拒绝，且不留下通知）
5) 退出参与不产生通知
6) 回归：评论通知照常产生，未读数叠加正确
7) 前端：顶栏未读徽标、面板文案与列表页文案、点击参与类通知落项目详情（不带锚点）、
   点击评论类通知深链到该条评论（?comment=<id>）
"""
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request

from playwright.sync_api import sync_playwright

BASE = "http://localhost:5000/api"
FRONT = "http://localhost:3001"
MYSQL = r"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe"
DB_USER = "co_creation_esdk"
DB_PASS = "GchzPPQ8sM6Rc2Xn"
DB_NAME = "co_creation_esdk"

TS = str(int(time.time()))[-6:]
PASSWORD = "test123456"
SETTLE = 0.8  # 通知是 fire-and-forget，写入晚于接口响应

assert_fails = []
console_errors = []


def api(path, data=None, token=None, method=None):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(data).encode() if data is not None else None,
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
        method=method or ("POST" if data is not None else "GET"),
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def sql(statement):
    subprocess.run(
        [MYSQL, "-u", DB_USER, f"-p{DB_PASS}", DB_NAME, "-e", statement],
        check=True,
        capture_output=True,
    )


def sql_one(statement):
    res = subprocess.run(
        [MYSQL, "-u", DB_USER, f"-p{DB_PASS}", DB_NAME, "-N", "-B", "-e", statement],
        check=True,
        capture_output=True,
        text=True,
    )
    return res.stdout.strip()


def check(label, cond):
    print(("  OK  " if cond else " FAIL ") + label)
    if not cond:
        assert_fails.append(label)


def attach(page):
    page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: console_errors.append(str(e)))


def unread_of(token):
    return api("/notifications/unread-count", token=token)["data"]["unread"]


def wait_unread(token, expect, timeout=6.0):
    """轮询未读数直到等于 expect 或超时。

    通知是 fire-and-forget 写入的，固定 `sleep(SETTLE)` 在机器负载高时跟不上，
    单次即时读会偶发拿到旧值造成假失败。_verify_common.wait_unread 是同一套逻辑，
    本脚本因为自带 api() 而保留本地版本。
    """
    deadline = time.time() + timeout
    value = unread_of(token)
    while value != expect and time.time() < deadline:
        time.sleep(0.25)
        value = unread_of(token)
    return value


def main():
    def register(suffix):
        reg = api(
            "/users/register",
            {"username": f"pn{TS}{suffix}", "email": f"pn{TS}{suffix}@example.com", "password": PASSWORD},
        )
        return {"token": reg["data"]["token"], "user": reg["data"]["user"]}

    owner, b, c = register("o"), register("b"), register("c")
    uids = [owner["user"]["id"], b["user"]["id"], c["user"]["id"]]
    print("临时用户:", uids)

    pid = api(
        "/projects",
        {
            "title": f"参与通知验证项目 {TS}",
            "description": "这是一条用于验证参与共创通知与去重逻辑的临时项目描述，验证结束后会被完整清理。",
            "categoryId": 1,
        },
        token=owner["token"],
    )["data"]["id"]
    print("临时项目 id =", pid)

    try:
        # ============ A. 基线 ============
        check("发起人初始未读为 0", unread_of(owner["token"]) == 0)

        # ============ B. 有人参与 -> 通知发起人 ============
        api(f"/projects/{pid}/participate", {}, token=b["token"])
        time.sleep(SETTLE)
        check("有人参与后发起人收到 1 条未读", unread_of(owner["token"]) == 1)

        notif = api("/notifications", token=owner["token"])["data"]["notifications"]
        check("通知类型为 participate", notif[0]["type"] == "participate")
        check("通知 actor 是参与者本人", notif[0]["actor"]["id"] == b["user"]["id"])
        check("通知指向该项目", notif[0]["project"]["id"] == pid)
        check("参与通知没有评论预览", notif[0]["commentPreview"] is None)

        # ============ C. 去重：退出再加入 ============
        api(f"/projects/{pid}/participate", None, token=b["token"], method="DELETE")
        time.sleep(SETTLE)
        check("退出参与不产生通知", wait_unread(owner["token"], 1) == 1)

        api(f"/projects/{pid}/participate", {}, token=b["token"])
        check("同一人再次参与不重复通知", wait_unread(owner["token"], 1) == 1)
        check(
            "通知表里该 actor 仅有 1 条 participate",
            sql_one(
                f"SELECT COUNT(*) FROM notifications WHERE project_id = {pid} AND actor_id = {b['user']['id']} AND type = 'participate'"
            )
            == "1",
        )

        # ============ D. 另一位参与者各自一条 ============
        api(f"/projects/{pid}/participate", {}, token=c["token"])
        check("另一位伙伴参与产生第二条", wait_unread(owner["token"], 2) == 2)

        # ============ E. 自参与不通知 ============
        try:
            api(f"/projects/{pid}/participate", {}, token=owner["token"])
            check("创建者重复参与被拒（409）", False)
        except urllib.error.HTTPError as e:
            check("创建者重复参与被拒（409）", e.code == 409)
        time.sleep(0.4)
        check(
            "自参与不产生通知",
            sql_one(f"SELECT COUNT(*) FROM notifications WHERE project_id = {pid} AND actor_id = {owner['user']['id']}") == "0",
        )

        # ============ F. 回归：评论通知照常 ============
        reg_comment = api(
            f"/projects/{pid}/comments",
            {"content": "这个想法很有意思，期待后续的进展。"},
            token=b["token"],
        )["data"]["comment"]
        time.sleep(SETTLE)
        check("评论通知照常产生（未读累计到 3）", unread_of(owner["token"]) == 3)

        # ============ G. 前端 ============
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 950}, device_scale_factor=2)
            attach(page)
            page.goto(f"{FRONT}/login", wait_until="networkidle")
            page.evaluate(
                "([t, u]) => { localStorage.setItem('token', t); localStorage.setItem('userInfo', JSON.stringify(u)) }",
                [owner["token"], owner["user"]],
            )
            page.goto(f"{FRONT}/", wait_until="networkidle")
            page.wait_for_timeout(1600)

            badge = page.locator("[data-test='unread-badge']")
            check("顶栏未读徽标显示 3", badge.count() == 1 and badge.inner_text().strip() == "3")

            page.locator("button[title='通知']").click()
            page.wait_for_selector("[data-test='notif-panel']", timeout=3000)
            page.wait_for_timeout(600)
            items = page.locator("[data-test='notif-item']")
            check("面板列出 3 条通知", items.count() == 3)
            join_item = items.filter(has_text="参与了你的项目")
            check("面板出现「参与了你的项目」文案", join_item.count() == 2)
            join_texts = [join_item.nth(i).inner_text() for i in range(join_item.count())]
            check(
                "面板文案含两位参与者与项目名",
                any(f"pn{TS}b" in t for t in join_texts)
                and any(f"pn{TS}c" in t for t in join_texts)
                and all(f"参与通知验证项目 {TS}" in t for t in join_texts),
            )
            page.screenshot(path="docs/screenshots/participate-notif-panel-light.png")

            # 点击参与类通知 -> 项目详情页（不带 #comments）
            join_item.first.click()
            page.wait_for_timeout(1400)
            check(f"参与类通知落地项目详情（{page.url}）", f"/project/{pid}" in page.url)
            check("参与类通知不带 #comments 锚点", "#comments" not in page.url)

            # 独立通知页
            page.goto(f"{FRONT}/notifications", wait_until="networkidle")
            page.wait_for_timeout(1600)
            rows = page.locator("[data-test='notif-row']")
            check("通知页列出 3 条", rows.count() == 3)
            check(
                "通知页也有「参与了你的项目」",
                rows.filter(has_text="参与了你的项目").count() == 2,
            )
            page.screenshot(path="docs/screenshots/participate-notif-page-light.png")

            # 深色
            page.emulate_media(color_scheme="dark")
            page.wait_for_timeout(500)
            page.screenshot(path="docs/screenshots/participate-notif-page-dark.png")

            # 评论类通知深链到该条评论（自 825574d 起不再用 #comments 锚点）
            page.emulate_media(color_scheme="light")
            comment_row = page.locator("[data-test='notif-row']").filter(has_text="评论了你的项目")
            check("通知页有评论通知（回归）", comment_row.count() == 1)
            comment_row.first.click()
            page.wait_for_timeout(1400)
            check(
                f"评论类通知深链到该条评论（{page.url}）",
                f"comment={reg_comment['id']}" in page.url,
            )

            browser.close()
    finally:
        # 顺序：通知 -> 评论 -> 参与 -> 点赞 -> 项目 -> 用户
        sql(f"DELETE FROM notifications WHERE project_id = {pid};")
        sql(f"DELETE FROM project_comments WHERE project_id = {pid};")
        sql(f"DELETE FROM project_participants WHERE project_id = {pid};")
        sql(f"DELETE FROM project_likes WHERE project_id = {pid};")
        sql(f"DELETE FROM projects WHERE id = {pid};")
        # activity_logs 刻意不挂外键：级联删不掉，按项目与按用户各清一次
        sql(f"DELETE FROM activity_logs WHERE project_id = {pid};")
        sql(f"DELETE FROM activity_logs WHERE user_id IN ({','.join(str(i) for i in uids)});")
        sql(f"DELETE FROM users WHERE id IN ({','.join(str(i) for i in uids)});")
        print("已清理，项目残留:", sql_one(f"SELECT COUNT(*) FROM projects WHERE id = {pid}"))
        print("通知残留:", sql_one(f"SELECT COUNT(*) FROM notifications WHERE project_id = {pid}"))

    print("assert failed:", len(assert_fails))
    for f in assert_fails:
        print(" -", f)
    print("console errors:", len(console_errors))
    for e in console_errors[:5]:
        print(" -", e)
    sys.exit(1 if (assert_fails or console_errors) else 0)


if __name__ == "__main__":
    main()
