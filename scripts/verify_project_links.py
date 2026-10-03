# -*- coding: utf-8 -*-
"""「仓库地址 + 截止日期」接成真功能 · 端到端验证

背景：这两列线上一直有真实数据（各 10 行），但 `Project.js` **没声明**它们，
所以 `toClientProject` 取不到、接口不返回、前端更看不到 —— 典型的「死列」。
本脚本把它们接成功能，并钉住三个不做会更糟的边界。

用法（必须从仓库根目录跑）：
  "C:\\Users\\28916\\AppData\\Local\\Programs\\Python\\Python313\\python.exe" scripts/verify_project_links.py
"""
import os
import sys
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _verify_common import (  # noqa: E402
    api,
    attach,
    check,
    cleanup_project,
    cleanup_users,
    console_errors,
    crash,
    finish,
    inject_login,
    register,
    sql_one,
)

from playwright.sync_api import sync_playwright  # noqa: E402

FRONT = "http://localhost:3001"
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
UIDS = []
PIDS = []


class HTTPError400(Exception):
    """服务端按预期拒了（400）。用来把「脏输入被拒」与「脚本自己崩了」区分开 ——
    混在一起时，一个真 bug 会被当成「预期拒绝」而假绿。"""

# 相对今天：-1 已过期 / +30 未过期。用 SQL 拼出日期，避开 Python 时区。
PAST = sql_one("SELECT DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 1 DAY), '%Y-%m-%d')")
FUTURE = sql_one("SELECT DATE_FORMAT(DATE_ADD(CURDATE(), INTERVAL 30 DAY), '%Y-%m-%d')")


def make_project(token, title, **extra):
    body = {
        "title": title,
        "description": "验证仓库地址与截止日期的接线，长度满足服务端二十字门槛",
        "categoryId": 1,
        **extra,
    }
    try:
        data = api("/projects", body, token=token)
    except urllib.error.HTTPError as err:
        if err.code == 400:
            raise HTTPError400(err.code) from err
        raise
    return data["data"]["id"]


def main():
    user = register("projlink")
    UIDS.append(user["uid"])
    token = user["token"]
    name = user["user"]["username"]

    # ---------- A. 接口层 ----------
    print("\n== A. 接口层：两个字段真的出来了 ==")
    p1 = make_project(token, f"仓库+已截止 {name}", repositoryUrl="https://github.com/esdkaiyuan/demo",
                      endDate=PAST)
    PIDS.append(p1)
    d1 = api(f"/projects/{p1}")["data"]
    check("详情返回 repositoryUrl", d1.get("repositoryUrl") == "https://github.com/esdkaiyuan/demo")
    check("详情返回 endDate", d1.get("endDate") == PAST)

    p2 = make_project(token, f"未到期无仓库 {name}")
    PIDS.append(p2)
    d2 = api(f"/projects/{p2}")["data"]
    check("未填时 repositoryUrl 为 null（不是空串/undefined）",
          d2.get("repositoryUrl") is None)
    check("未填时 endDate 为 null", d2.get("endDate") is None)

    # 列表也要带（卡片将来要用）
    lst = api("/projects?pageSize=50")["data"]["projects"]
    item = next((x for x in lst if x["id"] == p1), None)
    check("列表接口同样返回这两个字段", item is not None and "repositoryUrl" in item and "endDate" in item)

    print("\n== B. 脏输入在写入侧就被拒（不是靠前端渲染时过滤）==")
    # 🔥 必须在**写入侧**拦。只靠前端过滤不够：脏值一旦落库，将来任何一处
    # 「把这个字段绑到 href」的改动都会重新打开 XSS 入口。拦在源头成本最低。
    # （前端 repoUrl 计算属性仍保留过滤，作为第二道防线 —— 但它不是唯一防线。）
    for bad, why in [
        ("javascript:alert(1)", "javascript 伪协议"),
        ("ftp://x.com/a", "非 http(s) 协议"),
        ("data:text/html,<script>alert(1)</script>", "data 伪协议"),
    ]:
        try:
            pid_bad = make_project(token, f"脏仓库{why}{name}", repositoryUrl=bad)
            PIDS.append(pid_bad)
            check(f"{why} 被拒（400）", False)
        except HTTPError400:
            check(f"{why} 被拒（400）", True)

    print("\n== B2. 非法截止日期同样被拒（2026-02-31 这种假日期要当场拦下）==")
    for bad, why in [("2026-02-31", "不存在的日期"), ("2026/01/01", "斜杠格式"), ("abc", "非日期")]:
        try:
            pid_bad = make_project(token, f"脏日期{why}{name}", endDate=bad)
            PIDS.append(pid_bad)
            check(f"{why} 被拒（400）", False)
        except HTTPError400:
            check(f"{why} 被拒（400）", True)

    print("\n== B3. 编辑能改也能清空 ==")
    p3 = make_project(token, f"可编辑仓库 {name}", repositoryUrl="https://github.com/a/b",
                      endDate=FUTURE)
    PIDS.append(p3)
    upd = api(f"/projects/{p3}", {"title": f"可编辑仓库 {name}",
                                  "description": "验证编辑与清空，长度满足服务端二十字门槛",
                                  "categoryId": 1, "endDate": PAST},
              token=token, method="PUT")["data"]
    check("编辑只改 endDate 时 repositoryUrl 保持不变",
          upd.get("repositoryUrl") == "https://github.com/a/b")
    check("编辑后 endDate 已更新", upd.get("endDate") == PAST)
    cleared = api(f"/projects/{p3}", {"title": f"可编辑仓库 {name}",
                                      "description": "验证编辑与清空，长度满足服务端二十字门槛",
                                      "categoryId": 1, "repositoryUrl": "", "endDate": ""},
                  token=token, method="PUT")["data"]
    check("传空串能真正清空两个字段（而不是被忽略）",
          cleared.get("repositoryUrl") is None and cleared.get("endDate") is None)

    # ---------- C. 页面层 ----------
    print("\n== C. 页面：仓库入口与已截止标记 ==")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1280, "height": 950}, device_scale_factor=2)
        page = attach(ctx.new_page())
        inject_login(page, token, user["user"])

        # ---------- C0. 表单录入（没有输入框，功能等于只做了一半）----------
        print("\n== C0. 表单：发布与编辑能录入这两个字段 ==")
        page.goto(f"{FRONT}/publish", wait_until="networkidle")
        page.wait_for_timeout(800)
        check("发布页有仓库地址输入框", page.locator("[data-test='form-repo']").count() == 1)
        check("发布页有截止日期输入框", page.locator("[data-test='form-end-date']").count() == 1)
        # 前端就地校验：填伪协议应当立刻报错，不靠往返 400
        page.locator("[data-test='form-repo']").fill("javascript:alert(1)")
        page.locator("[data-test='form-title']").fill("表单校验用标题足够长度")
        page.locator("[data-test='form-description']").fill(
            "验证前端就地校验，描述长度必须超过二十个字符才允许提交"
        )
        page.locator("[data-test='category-option']").first.click()
        page.locator("[data-test='submit-project']").click()
        page.wait_for_timeout(600)
        check("伪协议仓库地址被前端就地拦下（出现错误提示）",
              page.locator("[data-test='error-repo']").count() == 1)
        check("校验不通过时不发请求（URL 没跳到项目页）", "/project/" not in page.url)
        # 假日期：`type=date` 的输入框浏览器层面就会拒收非法值（Playwright 报 Malformed value），
        # 所以「用户根本填不进去」本身就是第一道防线；这里断言的正是这道防线生效。
        # 纯逻辑层的真实性校验（2026-02-31 被悄悄滚到 3 月）由 validateEndDate 覆盖，
        # 已在 B2 段用接口层证明。
        page.locator("[data-test='form-repo']").fill("https://github.com/a/b")
        malformed_rejected = False
        try:
            page.locator("[data-test='form-end-date']").fill("2026-02-31")
        except Exception:  # noqa: BLE001 - Playwright 对非法 date 值抛错正是期望行为
            malformed_rejected = True
        check("非法日期被浏览器输入框当场拒收（填都填不进去）", malformed_rejected)
        # 合法值：走发布流程，验证真的存进去了
        page.locator("[data-test='form-end-date']").fill(FUTURE)
        page.locator("[data-test='submit-project']").click()
        page.wait_for_timeout(1800)
        check("填了合法值后能发布成功并跳到详情页", "/project/" in page.url)
        new_pid = int(page.url.rstrip("/").split("/")[-1])
        PIDS.append(new_pid)
        created = api(f"/projects/{new_pid}", token=token)["data"]
        check("发布时仓库地址真的落库了",
              created.get("repositoryUrl") == "https://github.com/a/b")
        check("发布时截止日期真的落库了", created.get("endDate") == FUTURE)

        # 编辑页回填 + 清空
        page.goto(f"{FRONT}/project/{new_pid}/edit", wait_until="networkidle")
        page.wait_for_timeout(1000)
        check("编辑页回填了仓库地址",
              page.locator("[data-test='form-repo']").input_value() == "https://github.com/a/b")
        check("编辑页回填了截止日期",
              page.locator("[data-test='form-end-date']").input_value() == FUTURE)
        page.locator("[data-test='form-repo']").fill("")
        page.locator("[data-test='form-end-date']").fill("")
        page.locator("[data-test='submit-project']").click()
        page.wait_for_timeout(1600)
        cleared2 = api(f"/projects/{new_pid}", token=token)["data"]
        check("编辑时清空两项后真的存成 null",
              cleared2.get("repositoryUrl") is None and cleared2.get("endDate") is None)

        # C1. 有仓库 + 已截止
        page.goto(f"{FRONT}/project/{p1}", wait_until="networkidle")
        page.wait_for_timeout(800)
        repo = page.locator("[data-test='detail-repo']")
        check("有仓库地址时渲染「查看仓库」入口", repo.count() == 1)
        check("入口 href 与库里一致",
              repo.get_attribute("href") == "https://github.com/esdkaiyuan/demo")
        check("站外链接必须 rel=noopener（防 tabnabbing）",
              "noopener" in (repo.get_attribute("rel") or ""))
        check("target=_blank 存在", repo.get_attribute("target") == "_blank")

        exp = page.locator("[data-test='detail-expired']")
        check("过期项目显示「已截止」标记", exp.count() == 1)
        # 页面按「2026 年 10 月 2 日」渲染（中文习惯），库里存的是 2026-10-02。
        # 断言要比**渲染后的形态**，否则改个文案格式就假红。
        _y, _m, _d = PAST.split("-")
        expect_text = f"{_y} 年 {int(_m)} 月 {int(_d)} 日"
        check(f"已截止文案里带具体日期（{expect_text}）", expect_text in (exp.inner_text() or ""))

        # C2. 未填的：不渲染任何入口
        page.goto(f"{FRONT}/project/{p2}", wait_until="networkidle")
        page.wait_for_timeout(800)
        check("未填仓库时不渲染仓库入口", page.locator("[data-test='detail-repo']").count() == 0)
        check("未填截止日期时不渲染已截止标记",
              page.locator("[data-test='detail-expired']").count() == 0)

        # C3. 未过期项目不该显示「已截止」
        p4 = make_project(token, f"未到期 {name}", endDate=FUTURE)
        PIDS.append(p4)
        page.goto(f"{FRONT}/project/{p4}", wait_until="networkidle")
        page.wait_for_timeout(800)
        check("未到期项目不显示「已截止」",
              page.locator("[data-test='detail-expired']").count() == 0)

        # C5. 零 console 错误
        page.goto(f"{FRONT}/project/{p1}", wait_until="networkidle")
        page.wait_for_timeout(600)
        check(f"全程零 console 错误（{len(console_errors)} 条）", not console_errors)

        # ---------- D. 截图 ----------
        import os as _os
        _os.makedirs("docs/screenshots", exist_ok=True)
        page.goto(f"{FRONT}/project/{p1}", wait_until="networkidle")
        page.wait_for_timeout(700)
        page.screenshot(path="docs/screenshots/project-links-light.png", full_page=False)
        page.emulate_media(color_scheme="dark")
        page.wait_for_timeout(600)
        page.screenshot(path="docs/screenshots/project-links-dark.png", full_page=False)
        print("截图: docs/screenshots/project-links-{light,dark}.png")

        ctx.close()
        browser.close()


if __name__ == "__main__":
    try:
        main()
    except BaseException as err:  # noqa: BLE001 - 崩溃必须记账，否则 finish() 会报「0 失败」的假绿
        crash(err)
        import traceback
        traceback.print_exc()
    finally:
        for pid in PIDS:
            cleanup_project(pid, UIDS)
        if UIDS:
            cleanup_users(UIDS)
        print(
            "残留项目:",
            sql_one(f"SELECT COUNT(*) FROM projects WHERE id IN ({','.join(map(str, PIDS)) or '0'})"),
        )
        print(
            "残留用户:",
            sql_one(f"SELECT COUNT(*) FROM users WHERE id IN ({','.join(map(str, UIDS)) or '0'})"),
        )
        finish()
