#!/usr/bin/env python3
"""@ 提及端到端验证：解析 → 通知 → 高亮 → 补全。

口径（唯一事实：backend comment.service 的 extractMentionNames / resolveMentions）：
- 识别：@ 到空白或常见标点为止，2-20 字符；查不到的用户名静默忽略；作者自己排除
- 通知：type='mention'，与 comment/reply 独立（同一人既被回复又被 @ 收两条）
- 高亮：前端只认响应 mentionNames（整库识别口径），不会假高亮
- 补全：行尾 @ 触发候选（本页评论作者，排除自己）

跑法：C:/Users/28916/AppData/Local/Programs/Python/Python313/python.exe scripts/verify_mentions.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _verify_common import (  # noqa: E402
    BASE,
    api,
    check,
    cleanup_project,
    create_project,
    crash,
    finish,
    inject_login,
    register,
    sql,
    sql_one,
)

from playwright.sync_api import sync_playwright  # noqa: E402

TS = time.strftime("%m%d%H%M%S")
PIDS, UIDS = [], []


def mention_rows(where):
    # 只按 uid 过滤（uid 是本次注册的临时账号，天然干净）；
    # 别用 username LIKE 匹配 TS——register 用的是 _verify_common 模块自己的 TS，
    # 与脚本运行的 TS 差几秒，LIKE 永远不命中（实测 A2/A4 假红根因）
    #
    # WHERE 里的 n.user_id 依赖 FROM 上的别名 n：漏了别名 mysql 会报
    # Unknown column，整个脚本在 A2 崩掉 —— 而崩溃一度被下方的 except 吞成 exit 0，
    # 结果是「A2~A8 与整段页面测试都没跑，汇总却显示 PASS」的假绿。别名必须写。
    return int(sql_one(
        f"SELECT COUNT(*) FROM notifications n WHERE type = 'mention' AND {where}"
    ) or 0)


def main():
    own = register("menown")
    ali = register("menali")
    bob = register("menbob")
    UIDS.extend([own["uid"], ali["uid"], bob["uid"]])
    pid = create_project(own["token"], f"@ 提及验证项目{TS}")
    PIDS.append(pid)

    own_name = own["username"]
    ali_name = ali["username"]
    bob_name = bob["username"]

    print("\n== A. API：解析与通知 ==")
    # A1. @ 真实用户 -> 响应 mentions 带快照
    r1 = api(f"/projects/{pid}/comments", {"content": f"你好 @{own_name} 请看"}, token=ali["token"])
    got = (r1.get("data") or {}).get("mentions")
    check(
        "A1 @真实用户：响应 mentions == [{id, username}]",
        got == [{"id": own["uid"], "username": own_name}],
    )

    # A2. 被提及者收到 mention 通知（SQL 直查，排除 comment 通知的干扰）
    check("A2 被提及者收到 type='mention' 通知", mention_rows(f"n.user_id = {own['uid']}") == 1)

    # A3. @ 自己 / @ 不存在的人：识别只含真实存在的他人
    r2 = api(
        f"/projects/{pid}/comments",
        {"content": f"@{ali_name} @{bob_name} 自己 @不存在的人{TS}"},
        token=bob["token"],
    )
    got2 = (r2.get("data") or {}).get("mentions") or []
    check(
        "A3 @自己与@不存在者被排除：mentions 只含 ali",
        [m.get("username") for m in got2] == [ali_name],
    )
    check("A4 ali 收到 mention 通知", mention_rows(f"n.user_id = {ali['uid']}") == 1)
    check("A5 bob 自己 @ 自己不通知", mention_rows(f"n.user_id = {bob['uid']}") == 0)

    # A6. 无 @ 的评论 mentions 为空数组
    r3 = api(f"/projects/{pid}/comments", {"content": f"普通评论，没有提及 {TS}"}, token=ali["token"])
    got3 = (r3.get("data") or {}).get("mentions")
    check("A6 无 @ 评论：mentions == []", got3 == [])

    # A7. 通知列表接口带出 mention 类型（深链含 commentId）
    inbox = api("/notifications", token=own["token"])
    rows = (inbox.get("data") or {}).get("notifications") or []
    mrow = next((n for n in rows if n.get("type") == "mention"), None) or {}
    check(
        "A7 通知列表出现 mention 行且带 commentId 深链",
        bool(mrow) and mrow.get("commentId") is not None,
    )

    # A8. mention 通知不虚增 comment_count
    cnt = sql_one(f"SELECT comment_count FROM projects WHERE id = {pid}")
    check("A8 comment_count 与真实评论数一致（mention 不虚增）", cnt == "3")

    print("\n== B. 页面：高亮 / 文案 / 补全 ==")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        inject_login(page, own["token"], own["user"])

        # B1. 详情页评论里 @own 高亮
        page.goto(f"http://localhost:3001/project/{pid}", wait_until="networkidle")
        page.wait_for_selector("[data-test='comment-item']", timeout=8000)
        hi = page.locator("[data-test='mention']").filter(has_text=f"@{own_name}")
        check("B1 详情页 @own 渲染高亮", hi.count() >= 1)

        # B2. 通知页 mention 文案
        page.goto("http://localhost:3001/notifications", wait_until="networkidle")
        page.wait_for_selector("[data-test='notif-row']", timeout=8000)
        body = page.locator("body").inner_text()
        check("B2 通知页出现「在评论中提及了你」", "在评论中提及了你" in body)

        # B3. 补全浮层：输入 @ 弹出候选（ali/bob 都评论过 -> 候选含他们）
        page.goto(f"http://localhost:3001/project/{pid}", wait_until="networkidle")
        box = page.locator("[data-test='comment-input']")
        box.wait_for(state="visible", timeout=8000)
        box.fill("看看 ")
        box.type("@")
        pop = page.locator("[data-test='mention-pop']")
        pop.wait_for(state="visible", timeout=3000)
        opts = pop.locator("[data-test='mention-option']").all_inner_texts()
        check(
            "B3 输入 @ 弹候选（含 ali）",
            any(ali_name in t for t in opts),
        )
        # B4. 点候选 -> 草稿以 @ali<空格> 结尾
        pop.locator("[data-test='mention-option']").first.click()
        val = box.input_value()
        check(f"B4 点选补全后草稿以 @{ali_name} 结尾", val.strip().endswith(f"@{ali_name}"))
        check("B5 补全后浮层收起", page.locator("[data-test='mention-pop']").count() == 0)

        # B6. token 过滤：@al 只留 ali（bob 不匹配）
        box.fill("")
        box.type("@al")
        opts2 = page.locator("[data-test='mention-option']").all_inner_texts()
        check("B6 候选按片段过滤（al 只命中 ali）", opts2 and all(ali_name in t for t in opts2))

        ctx.close()
        browser.close()


if __name__ == "__main__":
    try:
        main()
    except BaseException as err:  # noqa: BLE001 - 清场优先，但崩溃必须记账
        # 这一段曾经是**假绿**：崩溃被 except 吞掉，而 finish() 只看
        # assert_fails / console_errors（崩溃两者都不碰）-> 退出码 0、汇总 PASS，
        # 实际 A2~A8 与整段页面测试全都没跑。已实测复现。
        # 修法：crash() 把崩溃登记成一次失败，finish() 必然退出 1。
        # 其余 4 个同类脚本（counter_atomicity / popular_tags / project_flags /
        # rich_text）本来就有 _ERRORED -> sys.exit(1)，行为是对的，别照抄这段。
        crash(err)
        import traceback

        traceback.print_exc()
    finally:
        for pid in PIDS:
            cleanup_project(pid, UIDS)
        print(
            "残留项目:",
            sql_one(f"SELECT COUNT(*) FROM projects WHERE id IN ({','.join(map(str, PIDS)) or '0'})"),
        )
        print(
            "残留用户:",
            sql_one(f"SELECT COUNT(*) FROM users WHERE id IN ({','.join(map(str, UIDS)) or '0'})"),
        )
        finish()
