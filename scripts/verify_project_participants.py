# -*- coding: utf-8 -*-
"""项目「共创伙伴」验证

覆盖：
1) GET /projects/:id/participants 契约（结构 / 分页 / 未登录可访问 / 404）
2) 详情接口内嵌 participants 预览（≤8 条、发起人置顶、计数取自中间表真实行数）
3) 详情页侧边栏「共创伙伴」卡：计数文案、头像堆叠（6 个 + 「+N」）
4) 「查看全部共创伙伴」弹层：完整名单、发起人徽章、Esc 关闭
5) 参与 / 退出即时联动：头像堆叠与计数不刷新页面即变
6) 历史计数漂移自愈：participant_count 与中间表行数不一致时以真实行数为准并回写
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
TOTAL = 8  # 1 位发起人 + 7 位共创伙伴

assert_fails = []
console_errors = []

# 模块级兜底：注册接口限流 429 可能在任何一步抛出（本脚本要建 8 个账号，最容易撞），
# 注册/造数时立刻登记，顶层 finally 才能把已经建出来的临时数据清掉。
# ⚠️ 旧结构把注册写在 main() 的 try 之外，429 时 finally 不执行 —— 实测漏了 5 个账号。
PIDS = []
UIDS = []


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


def inject_login(page, token, user):
    page.goto(f"{FRONT}/login", wait_until="networkidle")
    page.evaluate(
        "([t, u]) => { localStorage.setItem('token', t); localStorage.setItem('userInfo', JSON.stringify(u)) }",
        [token, user],
    )


def count_text(page):
    return page.locator("[data-test='participants-count']").inner_text().strip()


def stack_state(page):
    return (
        page.locator("[data-test='participant-avatar']").count(),
        page.locator("[data-test='participant-overflow']").count(),
    )


def main():
    users = []
    for i in range(TOTAL):
        reg = api(
            "/users/register",
            {"username": f"part{TS}{i}", "email": f"part{TS}{i}@example.com", "password": PASSWORD},
        )
        users.append({"token": reg["data"]["token"], "user": reg["data"]["user"]})
        UIDS.append(reg["data"]["user"]["id"])
    creator, member = users[0], users[1]
    uids = [u["user"]["id"] for u in users]
    print(f"临时用户 {TOTAL} 个:", uids)

    pid = api(
        "/projects",
        {
            "title": f"共创伙伴验证项目 {TS}",
            "description": "这是一条用于验证共创伙伴展示与即时联动的临时项目描述，验证结束后会被完整清理。",
            "categoryId": 1,
        },
        token=creator["token"],
    )["data"]["id"]
    PIDS.append(pid)
    print("临时项目 id =", pid)

    try:
        # ============ A. 另 7 位加入 ============
        for u in users[1:]:
            api(f"/projects/{pid}/participate", {}, token=u["token"])
        check(
            f"中间表共 {TOTAL} 条参与记录",
            sql_one(f"SELECT COUNT(*) FROM project_participants WHERE project_id = {pid}") == str(TOTAL),
        )

        # ============ B. 接口契约 ============
        pub = api(f"/projects/{pid}/participants")["data"]
        check("未登录也可访问名单（公开接口）", "participants" in pub)
        check("返回结构含 participants/total/page/pageSize", {"participants", "total", "page", "pageSize"} <= set(pub))
        check(f"total = {TOTAL}", pub["total"] == TOTAL)
        check("发起人排在首位", pub["participants"][0]["role"] == "creator")
        check(
            "每条含 id/username/avatar/role/joinedAt",
            {"id", "username", "avatar", "role", "joinedAt"} <= set(pub["participants"][0]),
        )

        p1 = api(f"/projects/{pid}/participants?page=1&pageSize=3")["data"]
        check("pageSize=3 生效", len(p1["participants"]) == 3)
        check("page=1 且 total 不变", p1["page"] == 1 and p1["total"] == TOTAL)
        p3 = api(f"/projects/{pid}/participants?page=3&pageSize=3")["data"]
        check("末页只剩 2 条", len(p3["participants"]) == 2 and p3["page"] == 3)

        try:
            api("/projects/999999/participants")
            check("不存在项目返回 404", False)
        except urllib.error.HTTPError as e:
            check("不存在项目返回 404", e.code == 404)

        # ============ C. 详情内嵌预览 + 计数自愈 ============
        detail = api(f"/projects/{pid}")["data"]
        check("详情内嵌名单有预览", len(detail["participants"]) == TOTAL)
        check("详情计数与中间表一致", detail["participantCount"] == TOTAL)
        check("详情携带发起人信息", bool(detail.get("creator")) and detail["creator"]["id"] == uids[0])
        check("详情携带分类名", bool(detail.get("categoryName")))

        sql(f"UPDATE projects SET participant_count = 0 WHERE id = {pid};")
        drift = api(f"/projects/{pid}")["data"]
        check("计数漂移时详情返回真实行数", drift["participantCount"] == TOTAL)
        time.sleep(0.8)
        check("漂移已异步回写自愈", sql_one(f"SELECT participant_count FROM projects WHERE id = {pid}") == str(TOTAL))

        # ============ D. 前端：详情页共创伙伴卡 ============
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 1000}, device_scale_factor=2)
            attach(page)
            inject_login(page, member["token"], member["user"])
            page.goto(f"{FRONT}/project/{pid}", wait_until="networkidle")
            page.wait_for_timeout(1500)

            # 主内容区未被改动波及
            check("详情页主标题渲染", page.locator("h1").inner_text().strip() == f"共创伙伴验证项目 {TS}")
            check("项目介绍卡渲染", page.get_by_text("项目介绍", exact=True).count() == 1)
            check("发起人卡显示真实发起人", page.get_by_text(f"part{TS}0", exact=True).count() >= 1)
            page.evaluate("() => window.scrollTo(0, 0)")
            page.wait_for_timeout(600)
            page.screenshot(path="docs/screenshots/participants-detail-top.png")

            card = page.locator("[data-test='open-participants']")
            card.scroll_into_view_if_needed()
            page.wait_for_timeout(400)
            check("侧边栏出现「共创伙伴」卡", card.count() == 1)
            check(f"计数显示「{TOTAL} 位」", count_text(page) == f"{TOTAL} 位")

            avatars, overflow = stack_state(page)
            check(f"头像堆叠 6 个（实际 {avatars}）", avatars == 6)
            check(
                "超出部分折叠为「+2」",
                overflow == 1 and page.locator("[data-test='participant-overflow']").inner_text().strip() == "+2",
            )
            page.screenshot(path="docs/screenshots/participants-detail-light.png")

            # ============ E. 弹层：完整名单 ============
            card.click()
            page.wait_for_selector("[data-test='participants-modal']", timeout=3000)
            page.wait_for_timeout(700)
            rows = page.locator("[data-test='participant-row']")
            check(f"弹层列出全部 {TOTAL} 位", rows.count() == TOTAL)
            check("弹层文案为「共 8 位伙伴」", f"共 {TOTAL} 位" in page.locator("[data-test='participants-total']").inner_text())
            check("发起人被标记徽章", page.locator("[data-test='participants-modal']").get_by_text("发起人", exact=True).count() == 1)
            check(
                "名单首位是发起人本人",
                f"part{TS}0" in rows.first.inner_text(),
            )
            check(
                "成员带角色与加入时间",
                "项目发起人" in rows.first.inner_text() and "加入" in rows.first.inner_text(),
            )
            check("总数为 8 时不显示「加载更多」", page.locator("[data-test='load-more-participants']").count() == 0)
            page.screenshot(path="docs/screenshots/participants-modal-light.png")

            # Esc 关闭
            page.keyboard.press("Escape")
            page.wait_for_selector("[data-test='participants-modal']", state="detached", timeout=3000)
            check("Esc 可关闭弹层", page.locator("[data-test='participants-modal']").count() == 0)
            check("关闭后 body 滚动恢复", page.evaluate("() => document.body.style.overflow") == "")

            # ============ F. 参与 / 退出即时联动 ============
            exit_btn = page.locator("aside button").filter(has_text="已参与")
            exit_btn.click()
            page.wait_for_timeout(900)
            check("退出后计数即时回落", count_text(page) == f"{TOTAL - 1} 位")
            avatars, overflow = stack_state(page)
            check(
                "退出后堆叠即时变为 6 + 「+1」",
                avatars == 6
                and page.locator("[data-test='participant-overflow']").inner_text().strip() == "+1",
            )
            check(
                "服务端也同步退出",
                api(f"/projects/{pid}/participants")["data"]["total"] == TOTAL - 1,
            )

            join_btn = page.locator("aside button").filter(has_text="参与共创")
            join_btn.click()
            page.wait_for_timeout(900)
            check("重新参与后计数即时恢复", count_text(page) == f"{TOTAL} 位")
            check(
                "重新参与后堆叠恢复为「+2」",
                page.locator("[data-test='participant-overflow']").inner_text().strip() == "+2",
            )
            check("服务端也同步参与", api(f"/projects/{pid}/participants")["data"]["total"] == TOTAL)
            check("参与后按钮回到「已参与」", page.locator("aside button").filter(has_text="已参与").count() == 1)
            page.screenshot(path="docs/screenshots/participants-detail-after-join.png")

            # ============ G. 深色模式 ============
            page.emulate_media(color_scheme="dark")
            page.wait_for_timeout(500)
            page.screenshot(path="docs/screenshots/participants-detail-dark.png")
            card.click()
            page.wait_for_selector("[data-test='participants-modal']", timeout=3000)
            page.wait_for_timeout(600)
            page.screenshot(path="docs/screenshots/participants-modal-dark.png")

            browser.close()
    finally:
        # 先清中间表再删项目，避免级联链路过深；最后删用户
        # 注：参与共创自本轮起会通知发起人，所以要一并清掉通知
        sql(f"DELETE FROM notifications WHERE project_id = {pid};")
        sql(f"DELETE FROM project_participants WHERE project_id = {pid};")
        sql(f"DELETE FROM project_likes WHERE project_id = {pid};")
        sql(f"DELETE FROM projects WHERE id = {pid};")
        sql(f"DELETE FROM users WHERE id IN ({','.join(str(i) for i in uids)});")
        left = sql_one(f"SELECT COUNT(*) FROM projects WHERE id = {pid}")
        print("已清理临时项目与用户，项目残留:", left)

    print("assert failed:", len(assert_fails))
    for f in assert_fails:
        print(" -", f)
    print("console errors:", len(console_errors))
    for e in console_errors[:5]:
        print(" -", e)
    sys.exit(1 if (assert_fails or console_errors) else 0)


if __name__ == "__main__":
    try:
        main()
    finally:
        # 兜底清理：注册/造数阶段就失败（如 429）时上面的 finally 根本没机会跑
        for pid in PIDS:
            sql(f"DELETE FROM notifications WHERE project_id = {pid};")
            sql(f"DELETE FROM project_participants WHERE project_id = {pid};")
            sql(f"DELETE FROM project_likes WHERE project_id = {pid};")
            sql(f"DELETE FROM projects WHERE id = {pid};")
        if UIDS:
            sql(f"DELETE FROM users WHERE id IN ({','.join(str(i) for i in UIDS)});")
            print("兜底清理完成，剩余临时用户:",
                  sql_one(f"SELECT COUNT(*) FROM users WHERE id IN ({','.join(str(i) for i in UIDS)})"))
