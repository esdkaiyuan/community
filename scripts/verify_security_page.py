# -*- coding: utf-8 -*-
"""账号安全页（/security）端到端验证。

补的是上一轮记录在案的缺口 ④：安全事件与操作日志**只有后端与接口，没有前端页面**。
这一轮把两条只读接口搬上了界面，所以这个脚本要同时守住三件事：

  1. **页面真的把数据渲染出来了**（不是空壳）：标签、解释文案、来源、聚合次数。
  2. **敏感信息没有因为上屏而泄漏**：日志里存的是脱敏账号，页面上也不能出现明文邮箱 / 用户名。
     —— 这是本页最容易被「顺手改进」破坏的性质（比如有人为了「友好」把 account 换成真实邮箱）。
  3. **前后端枚举口径一致**：前端的词表（utils/audit.js）必须覆盖后端的白名单，
     否则某一类事件会静默显示成兜底文案「异常尝试」，没人发现。
     顺带钉住「筛选 chip 不许有假入口」—— 每个 chip 都必须真能筛出行来。

分段：
  A 接口层：/logs/me/security 的聚合、脱敏、归属、越权不可见、坏参数
  B 词表口径：前端 EVENT_LABELS / ACTION_ICONS / EVENT_FILTERS ↔ 后端白名单 + AppIcon 图标表
  C 页面层（Playwright）：未登录跳转、渲染、筛选、空状态、脱敏、窄屏、深浅色截图
  D 清理与对账

跑法（**仓库根目录**）：
    "C:\\Users\\28916\\AppData\\Local\\Programs\\Python\\Python313\\python.exe" scripts/verify_security_page.py
⚠️ 必须用系统 Python：managed 的 ~/.workbuddy/binaries/python 没装 playwright，
   会在 import 处 ModuleNotFoundError，而对外表现是「OK=0 / FAIL=0 / 退出码 1」，极易误读。
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _verify_common import (  # noqa: E402
    FRONT,
    PASSWORD,
    TS,
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
    security_event_rows,
    sql,
    sql_one,
)

ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "docs" / "screenshots"

UIDS = []  # 只增不减：清理按它循环，中途摘掉谁就等于漏清谁
PIDS = []

LOGIN_FAILS = 4  # 连续失败次数，用来验证聚合

# 浏览器为每个失败请求自动记的网络日志，不是应用错误（JS 报错不带这个前缀）
NETWORK_LOG_PREFIX = "Failed to load resource"


# ---------------------------------------------------------------- 造数

def register_raw(username, email_pattern):
    """注册的**裸调用**：无论成败都把「真建出来的账号」登记进 UIDS。

    这条纪律是有代价换来的：断言「应当被拒」的注册用例，在实现有 bug 时会**真的建号成功**，
    只登记 201 分支就等于漏清。所以登记放在发请求的这个 helper 里，而不是由调用方分别处理。
    """
    email = email_pattern.format(username=username)
    status, body = api_status(
        "/users/register", {"username": username, "email": email, "password": PASSWORD}
    )
    uid = ((body.get("data") or {}).get("user") or {}).get("id")
    if uid:
        UIDS.append(uid)
    return status, body


def fail_login(email, times=LOGIN_FAILS, password="definitely-wrong-password"):
    """制造连续的登录失败（同时也在为「聚合」造数）"""
    for i in range(times):
        status, body = api_status("/users/login", {"email": email, "password": password})
        assert status == 401, f"第 {i + 1} 次失败登录预期 401，实际 {status}: {body}"


# ---------------------------------------------------------------- B 词表口径

def js_block(text, header, opener, closer):
    """从 JS 源码里切出某个常量字面量的**内容**（不含两侧的括号）"""
    start = text.index(header)
    start = text.index(opener, start) + 1
    return text[start : text.index(closer, start)]


def backend_enum(rel_path, const_name):
    """后端白名单：`const X = Object.freeze({ KEY: 'value' })` 里的 value 集合"""
    text = (ROOT / rel_path).read_text(encoding="utf-8")
    block = js_block(text, f"const {const_name} = Object.freeze(", "{", "}")
    return set(re.findall(r"'([\w.]+)'", block))


def frontend_keys(rel_path, header):
    """前端 `{ 'key': value }` 形式的**键**集合"""
    text = (ROOT / rel_path).read_text(encoding="utf-8")
    return set(re.findall(r"'([\w.]+)':", js_block(text, header, "{", "}")))


def frontend_values(rel_path, header):
    """前端 `{ 'key': value }` 形式的**值**集合。

    ⚠️ 键值要分清楚：ACTION_ICONS 的**键**是动作名（'project.create'），**值**才是图标名
    （'lightbulb'）。用取键的正则去查图标表，会拿一堆动作名去比对，必然全「缺」。
    """
    text = (ROOT / rel_path).read_text(encoding="utf-8")
    return set(re.findall(r": '([\w-]+)'", js_block(text, header, "{", "}")))


def frontend_filter_values(rel_path, header):
    """前端筛选数组里的 value（空串代表「全部」，不算一个枚举值）"""
    text = (ROOT / rel_path).read_text(encoding="utf-8")
    values = re.findall(r"value: '([^']*)'", js_block(text, header, "[", "]"))
    return {v for v in values if v}


def check_vocabulary():
    print("\n== B. 前后端枚举口径 ==")
    audit_rel = "frontend/src/utils/audit.js"
    backend_events = backend_enum("backend/src/services/securityEvent.service.js", "EVENTS")
    backend_actions = backend_enum("backend/src/services/activityLog.service.js", "ACTIONS")

    check(f"后端安全事件白名单抽到了（{sorted(backend_events)}）", len(backend_events) >= 3)

    event_labels = frontend_keys(audit_rel, "export const EVENT_LABELS = ")
    check(
        f"前端 EVENT_LABELS 覆盖后端全部事件（缺 {sorted(backend_events - event_labels)}）",
        backend_events <= event_labels,
    )
    action_icons = frontend_keys(audit_rel, "export const ACTION_ICONS = ")
    check(
        f"前端 ACTION_ICONS 覆盖后端全部动作（缺 {sorted(backend_actions - action_icons)}）",
        backend_actions <= action_icons,
    )

    # 图标名必须真在 AppIcon 表里：写错不会报错，只会静默回退成 sprout，每行都长成同一棵小苗
    icon_text = (ROOT / "frontend/src/components/AppIcon.vue").read_text(encoding="utf-8")

    def icon_exists(name):
        return f"'{name}': [" in icon_text or f"\n  {name}: [" in icon_text

    used_icons = frontend_values(audit_rel, "export const ACTION_ICONS = ")
    wanted = sorted(used_icons | {"shield", "history", "triangle-alert", "chevronRight"})
    missing = [n for n in wanted if not icon_exists(n)]
    check(f"页面用到的 {len(wanted)} 个图标都在 AppIcon 表里（缺 {missing}）", not missing)

    # 筛选值必须是真枚举，且必须都是「能落到我头上」的那几类 —— 反过来说，
    # 这里允许 EVENT_FILTERS 少于 EVENT_LABELS（token.rejected 无归属，筛不出来），
    # 但绝不允许出现一个后端不认的值（那就是永远筛出空列表的假入口）。
    event_filters = frontend_filter_values(audit_rel, "export const EVENT_FILTERS = ")
    action_filters = frontend_filter_values(audit_rel, "export const ACTION_FILTERS = ")
    check(
        f"安全事件筛选值都是真枚举（越界 {sorted(event_filters - backend_events)}）",
        event_filters <= backend_events,
    )
    check(
        f"操作类型筛选值都是真枚举（越界 {sorted(action_filters - backend_actions)}）",
        action_filters <= backend_actions,
    )


# ---------------------------------------------------------------- A 接口层

def check_api(owner, other, owner_username, owner_email):
    print("\n== A. 接口层 ==")

    resp = api("/logs/me/security", token=owner["token"])
    events = resp["data"]["events"]
    total = resp["data"]["total"]

    login = [e for e in events if e["event"] == "auth.login.rejected"]
    reg = [e for e in events if e["event"] == "auth.register.rejected"]

    check(f"连续 {LOGIN_FAILS} 次登录失败被聚合成 1 行", len(login) == 1)
    check(
        f"聚合次数精确等于失败次数（occurrences={login[0]['occurrences'] if login else None}）",
        bool(login) and login[0]["occurrences"] == LOGIN_FAILS,
    )
    check(f"撞名注册被记为一条「注册尝试」（total={total}）", len(reg) == 1 and total == 2)

    # 脱敏：接口这一层就不许吐出明文（页面泄漏的先决条件是接口先给了）
    check(
        f"登录尝试的账号是脱敏形态（{login[0]['account'] if login else None}）",
        bool(login) and "***" in login[0]["account"] and "example.com" not in login[0]["account"],
    )
    check(
        f"注册尝试的账号是脱敏形态（{reg[0]['account'] if reg else None}）",
        bool(reg) and "***" in reg[0]["account"] and owner_username not in reg[0]["account"],
    )
    check(
        "接口响应里任何字段都不含明文邮箱",
        owner_email not in str(resp),
    )

    # 归属：两行都必须挂在我的 user_id 上（聚合键里含 targetUserId 就是为了不出「指错人」）
    rows = security_event_rows(f"target_user_id = {owner['uid']}")
    check(f"两条事件都归属到「被尝试的账号」（{len(rows)} 行）", len(rows) == 2)
    targets = {r["target_user_id"] for r in rows}
    check(f"两条事件的目标就是我的 id（{sorted(targets)}）", targets == {str(owner["uid"])})
    check(
        "时间列自洽（last_seen_at 不早于 created_at）",
        sql_one(
            f"SELECT COUNT(*) FROM security_events WHERE target_user_id = {owner['uid']} "
            "AND last_seen_at < created_at"
        )
        == "0",
    )

    # 越权：读得到什么由「你是谁」决定
    other_resp = api("/logs/me/security", token=other["token"])
    check(
        f"别人的 token 读不到针对我的事件（对方 total={other_resp['data']['total']}）",
        other_resp["data"]["total"] == 0,
    )

    # 坏参数：明确 400 且说人话，不静默忽略（静默忽略会让用户以为「筛过了，只是没数据」）
    status, body = api_status("/logs/me/security?event=__proto__", token=owner["token"])
    check(f"非法事件类型返回 400（实际 {status}）", status == 400)
    check(f"400 文案是中文人话（{body.get('message')!r}）", body.get("message") == "不支持的安全事件类型")

    status, _ = api_status("/logs/me/security")
    check(f"未登录读安全事件返回 401（实际 {status}）", status == 401)

    # 顺带回归上一轮的核心结论：缺 token 的正常 401 不该写安全事件（负向断言）
    before = int(sql_one("SELECT COUNT(*) FROM security_events") or 0)
    api_status("/logs/me/security")
    after = int(sql_one("SELECT COUNT(*) FROM security_events") or 0)
    check(f"缺 token 的 401 不写安全事件（{before} → {after}）", before == after)

    # 操作日志接口：页面另一半的数据源
    logs = api("/logs/me", token=owner["token"])["data"]
    actions = {l["action"] for l in logs["logs"]}
    check(f"操作日志含发布记录（{sorted(actions)}）", "project.create" in actions)
    check("操作日志含资料变更记录", "user.profile.update" in actions)
    check("操作日志的条数与库一致", logs["total"] == int(sql_one(f"SELECT COUNT(*) FROM activity_logs WHERE user_id = {owner['uid']}") or 0))
    return total


# ---------------------------------------------------------------- C 页面层

def check_page(browser, owner, other, owner_username, owner_email, api_total):
    print("\n== C. 页面层 ==")

    # C0. 未登录：受限页应跳登录（页面上不该闪现任何数据）
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = attach(ctx.new_page())
    page.goto(f"{FRONT}/security", wait_until="networkidle")
    page.wait_for_timeout(400)
    check(f"未登录访问 /security 跳登录页（{page.url.split('/', 3)[-1]}）", "/login" in page.url)
    ctx.close()

    # C1. 登录态：安全提醒
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = attach(ctx.new_page())
    inject_login(page, owner["token"], owner["user"])
    page.goto(f"{FRONT}/security", wait_until="networkidle")
    page.wait_for_selector("[data-test='security-row']", timeout=10000)
    page.wait_for_timeout(500)

    rows = page.locator("[data-test='security-row']")
    check(f"安全提醒渲染出 {rows.count()} 行（预期 {api_total}）", rows.count() == api_total)

    subtitle = page.locator("[data-test='security-subtitle']").inner_text().strip()
    check(
        f"副标题的服务端真值正确（{subtitle!r}）",
        subtitle == f"有 {api_total} 条针对你账号的失败尝试",
    )
    check("有事件时出现总览条", page.locator("[data-test='security-summary']").is_visible())

    labels = sorted(t.strip() for t in page.locator("[data-test='security-event-label']").all_inner_texts())
    check(f"事件类型标签是中文而非枚举值（{labels}）", labels == ["注册尝试", "登录尝试"])

    list_text = page.locator("[data-test='security-list']").inner_text()
    check("登录类有解释性文案", "有人用你的邮箱尝试登录，但密码不对" in list_text)
    check("注册类有解释性文案", "有人想用你的用户名或邮箱注册新账号" in list_text)

    # 聚合次数上屏，且与库里的一致（不硬编码 4：以库为真值，避免脚本自己数字对不上）
    occ_text = page.locator("[data-test='security-occurrences']").first.inner_text()
    db_occ = security_event_rows(
        f"event = 'auth.login.rejected' AND target_user_id = {owner['uid']}"
    )[0]["occurrences"]
    check(f"聚合次数上屏且与库一致（页面「{occ_text.strip()}」/ 库 {db_occ}）", str(db_occ) in occ_text)

    # 🔥 本页最重要的负向断言：脱敏不能因为「上屏」而失守
    check("列表中不出现明文邮箱", owner_email not in list_text)
    check("列表中不出现明文用户名", owner_username not in list_text)
    check("整页都不出现明文邮箱", owner_email not in page.locator("body").inner_text())
    accounts = page.locator("[data-test='security-account']").all_inner_texts()
    check(f"账号列全部是脱敏形态（{accounts}）", bool(accounts) and all("***" in a for a in accounts))
    check("来源 IP 上屏", page.locator("[data-test='security-ip']").count() > 0)

    # C2. 筛选：**每个 chip 都必须真能筛出行来**（假入口是本仓库反复出现的坑）
    for label, value in [("登录", "auth.login.rejected"), ("注册", "auth.register.rejected")]:
        page.locator("[data-test='security-filter']", has_text=label).click()
        page.wait_for_timeout(700)
        got = page.locator("[data-test='security-row']").evaluate_all("els => els.map(e => e.dataset.event)")
        check(f"筛「{label}」能筛出结果（{len(got)} 行）—— 不是假入口", len(got) >= 1)
        check(f"筛「{label}」后只剩这一类事件", set(got) == {value})
        check(f"筛选写进 URL 可分享可后退（event={value}）", f"event={value}" in page.url)

    page.locator("[data-test='security-filter']", has_text="全部").click()
    page.wait_for_timeout(700)
    check(
        f"切回「全部」恢复全部 {api_total} 行",
        page.locator("[data-test='security-row']").count() == api_total,
    )

    # C3. 切到「我的操作」
    page.locator("[data-test='security-tab-activity']").click()
    page.wait_for_selector("[data-test='log-row']", timeout=10000)
    page.wait_for_timeout(400)
    check(f"切标签后 URL 带 tab=activity（{page.url.split('/', 3)[-1]}）", "tab=activity" in page.url)

    summaries = page.locator("[data-test='log-summary']").all_inner_texts()
    check(f"操作记录里有「发布项目」（{summaries}）", any("发布项目" in s for s in summaries))
    check("操作记录里有「更新个人资料」", any("更新个人资料" in s for s in summaries))

    log_total = int(sql_one(f"SELECT COUNT(*) FROM activity_logs WHERE user_id = {owner['uid']}") or 0)
    act_subtitle = page.locator("[data-test='security-subtitle']").inner_text().strip()
    check(f"操作视图的条数用服务端真值（{act_subtitle!r} / 库 {log_total}）", act_subtitle == f"共 {log_total} 条记录")

    # C4. 空状态：换一个「没人打过、也没做过事」的账号
    sql(f"DELETE FROM activity_logs WHERE user_id = {other['uid']};")
    ctx2 = browser.new_context(viewport={"width": 1440, "height": 900})
    page2 = attach(ctx2.new_page())
    inject_login(page2, other["token"], other["user"])
    page2.goto(f"{FRONT}/security", wait_until="networkidle")
    page2.wait_for_timeout(800)
    body2 = page2.locator("body").inner_text()
    check("没有事件时给出「没有发现异常尝试」空状态", "没有发现异常尝试" in body2)
    check("没有事件时不摆总览条（不吓唬人）", page2.locator("[data-test='security-summary']").count() == 0)
    check("没有事件时不渲染空列表容器", page2.locator("[data-test='security-list']").count() == 0)

    page2.locator("[data-test='security-tab-activity']").click()
    page2.wait_for_timeout(800)
    check("没有操作记录时给出空状态", "还没有操作记录" in page2.locator("body").inner_text())
    ctx2.close()

    # C5. 窄屏不得横向溢出（320 才逼得出真实瓶颈）
    for width, height, name in [(320, 720, "tiny"), (360, 780, "small"), (390, 844, "mobile")]:
        page.set_viewport_size({"width": width, "height": height})
        for query, view in [("", "安全提醒"), ("?tab=activity", "我的操作")]:
            page.goto(f"{FRONT}/security{query}", wait_until="networkidle")
            page.wait_for_timeout(500)
            over = page.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
            check(f"{name} {width}px 无横向溢出（{view}，多出 {over}px）", over <= 1)

    # C6. 深浅色截图（v-reveal 未滚到位的元素是 opacity:0，必须先滚再等）
    SHOTS.mkdir(parents=True, exist_ok=True)
    page.set_viewport_size({"width": 1440, "height": 900})
    for query, view, name in [("", "安全提醒", "security"), ("?tab=activity", "我的操作", "activity")]:
        for scheme in ("light", "dark"):
            page.emulate_media(color_scheme=scheme)
            page.goto(f"{FRONT}/security{query}", wait_until="networkidle")
            page.wait_for_timeout(600)
            target = page.locator("[data-test='security-list'], [data-test='activity-list']").first
            target.scroll_into_view_if_needed()
            page.wait_for_timeout(1600)
            page.screenshot(path=str(SHOTS / f"records-{name}-{scheme}.png"))
    page.emulate_media(color_scheme="light")
    check("深浅色截图已生成", (SHOTS / "records-security-dark.png").exists())

    # 入口：个人中心与顶栏用户菜单都能到这一页
    page.goto(f"{FRONT}/profile", wait_until="networkidle")
    page.wait_for_timeout(500)
    entry = page.locator("[data-test='profile-security-entry']")
    check("个人中心有「账号安全」入口", entry.count() == 1)
    entry.click()
    page.wait_for_url("**/security", timeout=6000)
    check(f"点入口进入账号安全页（{page.url.split('/', 3)[-1]}）", "/security" in page.url)

    ctx.close()


# ---------------------------------------------------------------- 主流程

def build_fixtures():
    """造数：两个临时账号 + 一批针对 owner 的失败尝试 + 一批 owner 的操作"""
    owner = register("secpg")
    UIDS.append(owner["uid"])
    other = register("secpt")
    UIDS.append(other["uid"])

    owner_username = owner["username"]
    owner_email = f"{owner_username}@example.com"

    # ① 连续登录失败 → 验证聚合（同一 IP / 同一账号 / 同一路径 → 一行带次数）
    fail_login(owner_email)

    # ② 撞名注册 → 针对 owner 的「注册尝试」（targetUserId 命中已存在的账号）
    status, body = register_raw(owner_username, "collide-{username}@example.com")
    assert status == 409, f"撞名注册预期 409，实际 {status}: {body}"

    # ③ owner 的操作日志：发布 + 编辑 + 改资料
    pid = create_project(owner["token"], f"账号安全页临时项目-{owner['uid']}", tags=["验证", "安全页"])
    PIDS.append(pid)
    api(
        f"/projects/{pid}",
        {"title": f"账号安全页临时项目（已编辑）-{owner['uid']}"},
        token=owner["token"],
        method="PUT",
    )
    api(
        "/users/profile",
        {"bio": f"验证账号安全页用临时简介 {TS}"},
        token=owner["token"],
        method="PUT",
    )

    print(f"临时账号 owner={owner['uid']} / other={other['uid']}，临时项目={pid}")
    return owner, other, owner_username, owner_email


def main():
    owner, other, owner_username, owner_email = build_fixtures()
    api_total = check_api(owner, other, owner_username, owner_email)
    check_vocabulary()

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            check_page(browser, owner, other, owner_username, owner_email, api_total)
        finally:
            browser.close()


def cleanup():
    for pid in PIDS:
        cleanup_project(pid)
    cleanup_users(UIDS)


if __name__ == "__main__":
    try:
        main()
    finally:
        # 故意访问 401 / 404 的请求会让浏览器记一条网络日志，那不是应用错误
        console_errors[:] = [e for e in console_errors if not e.startswith(NETWORK_LOG_PREFIX)]
        tracked = UIDS[:]
        cleanup()
        if tracked:
            ph = ",".join(str(i) for i in tracked)
            print(
                "cleanup: 残留测试用户",
                sql_one(f"SELECT COUNT(*) FROM users WHERE id IN ({ph})"),
                "| 残留操作日志",
                sql_one(f"SELECT COUNT(*) FROM activity_logs WHERE user_id IN ({ph})"),
                "| 残留安全事件(本机来源)",
                sql_one(
                    "SELECT COUNT(*) FROM security_events "
                    "WHERE ip IN ('127.0.0.1','::1','::ffff:127.0.0.1') OR ip IS NULL"
                ),
            )
    finish()
