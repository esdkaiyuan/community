# -*- coding: utf-8 -*-
"""修改登录密码（含「改密后旧令牌立即失效」）的端到端验证。

守四件事：

  1. **改密真的能改** —— 且只有知道当前密码的人能改（错密码必须 400 而不是 500）。
  2. **改密之后旧会话必须死** —— 这是「改密码」的全部意义。JWT 是无状态的，
     如果只换 password 列的哈希，一张已泄漏的令牌仍能用满 7 天。所以这里最核心的
     断言是「旧令牌 → 401」，而不是「返回 200」。
  3. **绝不记密码** —— 新旧密码都不许出现在 activity_logs / security_events 任何一列。
  4. **前后端口径一致** —— 上下界、maxlength、词表、图标全靠解析源码比对，不靠人工同步。

分段：
  A 接口层：PUT /users/password 的正常 / 校验 / 边界 / 会话作废 / 留痕 / 不泄漏
  B 源码口径：后端常量 ↔ 前端常量 ↔ 三个页面的 maxlength ↔ 词表与图标
  C 页面层（Playwright）：第三个 tab、表单锚点、就地红字、成功换令牌、窄屏、截图
  D 清理与对账

跑法（**仓库根目录**）：
    "C:\\Users\\28916\\AppData\\Local\\Programs\\Python\\Python313\\python.exe" scripts/verify_password_change.py

⚠️ 必须用系统 Python：managed 的 ~/.workbuddy/binaries/python 没装 playwright，
   会在 import 处 ModuleNotFoundError，而对外表现是「OK=0 / FAIL=0 / 退出码 1」。
⚠️ 本脚本会打 10~12 次 passwordLimiter（15 次 / 15 分钟）。连着跑两遍（中间不重启
   后端）会撞 429 —— 那不是功能坏了，重启后端即可清零。
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

UIDS = []  # 只增不减：清理按它循环
PIDS = []

# 浏览器为每个失败请求自动记的网络日志，不是应用错误（JS 报错不带这个前缀）
NETWORK_LOG_PREFIX = "Failed to load resource"

# 上下界从**后端源码**读回来做断言，不把 6 / 64 抄进脚本 —— 抄一份就等于
# 「测试与实现各写一份」，改了一侧另一边不会红。
_SVC_SRC = (ROOT / "backend/src/services/user.service.js").read_text(encoding="utf-8")
PW_MIN = int(re.search(r"const PASSWORD_MIN_LENGTH = (\d+)", _SVC_SRC).group(1))
PW_MAX = int(re.search(r"const PASSWORD_MAX_LENGTH = (\d+)", _SVC_SRC).group(1))

NEW_PW = f"NewPass!{TS}9z"      # 接口层成功用例的新密码（带时间戳，绝不与旧密码相同）
BOUND_PW = "b" * PW_MAX         # 「刚好上界」用的密码
UI_PW = f"UiNewPass!{TS}7k"     # 页面层成功用例的新密码

WRONG_CURRENT = "definitely-wrong-current-password"


# ---------------------------------------------------------------- 工具

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def js_block(text, header, opener, closer):
    """从 JS 源码里切出某个常量字面量的**内容**（不含两侧的括号）"""
    start = text.index(header)
    start = text.index(opener, start) + 1
    return text[start : text.index(closer, start)]


def change_pw(token, old, new):
    """改密请求。⚠️ 有 body 的 PUT 必须显式 method='PUT'（api 的默认 method 会变成 POST）"""
    return api_status(
        "/users/password",
        {"oldPassword": old, "newPassword": new},
        token=token,
        method="PUT",
    )


def user_hash(uid):
    return sql_one(f"SELECT password FROM users WHERE id = {uid}")


def token_version(uid):
    return sql_one(f"SELECT token_version FROM users WHERE id = {uid}")


def pw_events(uid):
    return security_event_rows(f"event = 'auth.password.rejected' AND target_user_id = {uid}")


def leak_hits(value, uids):
    """某个字面量出现在几张日志表的几行里。用来钉死「绝不记密码」。"""
    ph = ",".join(str(i) for i in uids)
    in_logs = sql_one(
        f"SELECT COUNT(*) FROM activity_logs WHERE user_id IN ({ph}) "
        f"AND (summary LIKE '%{value}%' OR CAST(detail AS CHAR) LIKE '%{value}%')"
    )
    in_events = sql_one(
        f"SELECT COUNT(*) FROM security_events WHERE target_user_id IN ({ph}) "
        f"AND (reason LIKE '%{value}%' OR CAST(account AS CHAR) LIKE '%{value}%' "
        f"OR path LIKE '%{value}%' OR CAST(user_agent AS CHAR) LIKE '%{value}%')"
    )
    return int(in_logs or 0) + int(in_events or 0)


# ---------------------------------------------------------------- A 接口层

def check_api():
    print("\n== A. 接口层：PUT /users/password ==")

    owner = register("pwdA")
    UIDS.append(owner["uid"])
    other = register("pwdB")
    UIDS.append(other["uid"])

    uid, token = owner["uid"], owner["token"]
    email = f"{owner['username']}@example.com"
    before_hash = user_hash(uid)

    check(f"新账号的 token_version 是 0（实际 {token_version(uid)}）", token_version(uid) == "0")

    # --- A1 未登录 ---
    status, _ = api_status("/users/password", {"oldPassword": PASSWORD, "newPassword": NEW_PW}, method="PUT")
    check(f"未登录改密返回 401（实际 {status}）", status == 401)

    # --- A2 当前密码错：400（不是 500）、不改密码、留一条可归属的安全事件 ---
    status, body = change_pw(token, WRONG_CURRENT, NEW_PW)
    check(f"当前密码不正确 → 400 而不是 500（实际 {status}）", status == 400)
    check(f"拒绝文案是中文人话（{body.get('message')!r}）", body.get("message") == "当前密码不正确")
    check("密码没有被改掉（哈希不变）", user_hash(uid) == before_hash)
    check("会话版本没有被推进（失败的尝试不该踢人下线）", token_version(uid) == "0")

    rows = pw_events(uid)
    check(f"当前密码不符被记成一条安全事件（{len(rows)} 行）", len(rows) == 1)
    check(
        f"安全事件 reason 是人话（{rows[0]['reason'] if rows else None}）",
        bool(rows) and rows[0]["reason"] == "当前密码不正确",
    )
    check(
        "安全事件里的账号是脱敏形态（不存明文邮箱）",
        bool(rows) and "***" in rows[0]["account"] and email not in rows[0]["account"],
    )
    check(
        f"安全事件路径指向改密接口（{rows[0]['path'] if rows else None}）",
        bool(rows) and rows[0]["path"].endswith("/users/password"),
    )
    check(
        f"安全事件归属到账号本人（target={rows[0]['target_user_id'] if rows else None}）",
        bool(rows) and rows[0]["target_user_id"] == str(uid),
    )

    # 再错一次 → 聚合进同一行（暴力尝试不该把表撑成洪水）
    change_pw(token, WRONG_CURRENT, NEW_PW)
    rows = pw_events(uid)
    check(
        f"重复失败被聚合（{len(rows)} 行 / occurrences={rows[0]['occurrences'] if rows else None}）",
        len(rows) == 1 and rows[0]["occurrences"] == 2,
    )

    # --- A3 新密码太短 / 太长：边界成对，且文案里的数字必须与真实上限一致 ---
    status, body = change_pw(token, PASSWORD, "a" * (PW_MIN - 1))
    check(f"新密码 {PW_MIN - 1} 位 → 400（实际 {status}）", status == 400)
    check(f"下界文案写的是真实常量（{body.get('message')!r}）", str(PW_MIN) in str(body.get("message")))

    status, body = change_pw(token, PASSWORD, "a" * (PW_MAX + 1))
    check(f"新密码 {PW_MAX + 1} 位 → 400（实际 {status}）", status == 400)
    check(f"上界文案写的是真实常量（{body.get('message')!r}）", str(PW_MAX) in str(body.get("message")))

    # --- A4 新密码与当前密码相同 ---
    status, body = change_pw(token, PASSWORD, PASSWORD)
    check(f"新密码与当前密码相同 → 400（实际 {status}）", status == 400)
    check(f"文案是中文人话（{body.get('message')!r}）", body.get("message") == "新密码不能与当前密码相同")

    # --- A5 坏输入不得 500 ---
    for label, payload in (
        ("新密码是数字", {"oldPassword": PASSWORD, "newPassword": 123456}),
        ("缺当前密码", {"newPassword": NEW_PW}),
        ("body 是空对象", {}),
    ):
        status, _ = api_status("/users/password", payload, token=token, method="PUT")
        check(f"{label} → 4xx 而不是 5xx（实际 {status}）", 400 <= status < 500)
    status, _ = api_status("/users/password", [], token=token, method="PUT")
    check(f"body 是数组 → 4xx 而不是 5xx（实际 {status}）", 400 <= status < 500)

    check("以上失败都没有改掉密码（哈希仍不变）", user_hash(uid) == before_hash)

    # --- A6 成功改密 ---
    status, body = change_pw(token, PASSWORD, NEW_PW)
    check(f"改密成功 → 200（实际 {status}）", status == 200)
    new_token = (body.get("data") or {}).get("token")
    check("响应换发了一张新令牌", bool(new_token))
    check("新令牌与旧令牌不同", bool(new_token) and new_token != token)
    check("密码哈希真的变了", user_hash(uid) != before_hash)
    check(f"token_version 推进到 1（实际 {token_version(uid)}）", token_version(uid) == "1")

    # --- A7 🔥 旧令牌立即失效（本脚本存在的核心理由）---
    status, _ = api_status("/users/me", token=token)
    check(f"改密后旧令牌访问 /users/me → 401（实际 {status}）", status == 401)
    status, _ = api_status("/users/profile", token=token)
    check(f"改密后旧令牌访问其它受保护接口 → 401（实际 {status}）", status == 401)

    status, body = api_status("/users/me", token=new_token)
    check(
        f"换发的新令牌照常可用（实际 {status}）",
        status == 200 and (body.get("data") or {}).get("id") == uid,
    )
    status, _ = api_status("/users/me", token=other["token"])
    check(f"别人的会话不受影响（实际 {status}）", status == 200)

    # 旧令牌走 optionalAuth 的公开端点：静默退化成「未登录」，不能 401、也不能刷安全事件
    pid = create_project(new_token, f"改密验证临时项目-{uid}", tags=["验证"])
    PIDS.append(pid)
    events_before = int(sql_one("SELECT COUNT(*) FROM security_events") or 0)
    status, _ = api_status(f"/projects/{pid}", token=token)
    check(f"旧令牌在公开详情页静默退化而不是 401（实际 {status}）", status == 200)
    events_after = int(sql_one("SELECT COUNT(*) FROM security_events") or 0)
    check(
        f"旧令牌的静默退化不写安全事件（{events_before} → {events_after}）",
        events_before == events_after,
    )

    # --- A8 旧密码不能再登录 / 新密码可以 ---
    status, _ = api_status("/users/login", {"email": email, "password": PASSWORD})
    check(f"旧密码不能再登录（实际 {status}）", status == 401)
    status, body = api_status("/users/login", {"email": email, "password": NEW_PW})
    check(f"新密码可以登录（实际 {status}）", status == 200)
    relogin = (body.get("data") or {}).get("token")
    check("重新登录拿到的令牌可用", bool(relogin) and api_status("/users/me", token=relogin)[0] == 200)

    # --- A9 审计留痕 + 不泄漏密码 ---
    logs = api("/logs/me", token=relogin)["data"]["logs"]
    pw_logs = [l for l in logs if l["action"] == "user.password.update"]
    check(f"改密写了一条审计日志（{len(pw_logs)} 条）", len(pw_logs) == 1)
    check(
        f"日志摘要是人话（{pw_logs[0]['summary'] if pw_logs else None}）",
        bool(pw_logs) and pw_logs[0]["summary"] == "修改了登录密码",
    )
    check(
        "日志 detail 为空（不含任何密码信息）",
        bool(pw_logs) and not pw_logs[0]["detail"],
    )

    leaked = leak_hits(PASSWORD, [uid]) + leak_hits(NEW_PW, [uid])
    check(f"新旧密码都没有出现在任何日志表（命中 {leaked} 行）", leaked == 0)

    # 前端「改密」筛选 chip 不是假入口：接口真能按这个类型筛出结果
    status, body = api_status("/logs/me/security?event=auth.password.rejected", token=relogin)
    check(
        f"安全事件接口能筛出改密类型（total={(body.get('data') or {}).get('total')}）",
        status == 200 and ((body.get("data") or {}).get("total") or 0) >= 1,
    )

    # --- A10 边界成对：刚好上界必须能通过（放在最后，它会再次作废令牌）---
    status, _ = change_pw(relogin, NEW_PW, BOUND_PW)
    check(f"刚好 {PW_MAX} 位的新密码可以通过（实际 {status}）", status == 200)
    check(f"token_version 再次推进到 2（实际 {token_version(uid)}）", token_version(uid) == "2")


# ---------------------------------------------------------------- B 源码口径

def check_sources():
    print("\n== B. 前后端枚举与常量口径（解析源码比对，不靠人工同步）==")

    fe = read("frontend/src/utils/password.js")
    f_min = int(re.search(r"export const PASSWORD_MIN_LENGTH = (\d+)", fe).group(1))
    f_max = int(re.search(r"export const PASSWORD_MAX_LENGTH = (\d+)", fe).group(1))
    check(f"最小长度前后端一致（后端 {PW_MIN} / 前端 {f_min}）", PW_MIN == f_min)
    check(f"最大长度前后端一致（后端 {PW_MAX} / 前端 {f_max}）", PW_MAX == f_max)

    for rel, label in (
        ("frontend/src/views/SecurityView.vue", "账号安全页"),
        ("frontend/src/views/RegisterView.vue", "注册页"),
    ):
        src = read(rel)
        bound = src.count(':maxlength="PASSWORD_MAX_LENGTH"')
        check(f"{label}的两个密码输入框都绑定了上界常量（{bound} 处）", bound == 2)
        check(f"{label}从 utils/password.js 取口径", "from '@/utils/password'" in src)

    # 全仓库不许再有硬编码的密码下界（登录页此前写死了 >= 6）
    stale = []
    for p in (ROOT / "frontend/src").rglob("*.vue"):
        if re.search(r"password[^\n]{0,40}length\s*>=\s*\d", p.read_text(encoding="utf-8")):
            stale.append(p.name)
    check(f"前端不再有硬编码的密码下界（命中 {stale}）", not stale)

    audit = read("frontend/src/utils/audit.js")
    check("动作图标表里有新动作（lock）", "'user.password.update': 'lock'" in audit)
    check("事件词表里有新事件（改密尝试）", "'auth.password.rejected': '改密尝试'" in audit)
    check("事件解释文案是写给用户看的人话", "试图修改你的登录密码" in audit)

    icon_src = read("frontend/src/components/AppIcon.vue")
    check("lock 图标已在 AppIcon 表里", re.search(r"^\s*lock:\s*\[", icon_src, re.M) is not None)

    backend_events = set(
        re.findall(
            r"'([\w.]+)'",
            js_block(read("backend/src/services/securityEvent.service.js"), "const EVENTS = Object.freeze(", "{", "}"),
        )
    )
    event_labels = set(re.findall(r"'([\w.]+)':", js_block(audit, "export const EVENT_LABELS = ", "{", "}")))
    check(
        f"EVENT_LABELS 覆盖后端全部事件（缺 {sorted(backend_events - event_labels)}）",
        backend_events <= event_labels,
    )

    event_filters = {
        v
        for v in re.findall(r"value: '([^']*)'", js_block(audit, "export const EVENT_FILTERS = ", "[", "]"))
        if v
    }
    check(
        f"改密已放进筛选 chip（{sorted(event_filters)}）",
        "auth.password.rejected" in event_filters,
    )
    check(
        f"筛选值都是后端真枚举（越界 {sorted(event_filters - backend_events)}）",
        event_filters <= backend_events,
    )

    backend_actions = set(
        re.findall(
            r"'([\w.]+)'",
            js_block(read("backend/src/services/activityLog.service.js"), "const ACTIONS = Object.freeze(", "{", "}"),
        )
    )
    action_icons = set(re.findall(r"'([\w.]+)':", js_block(audit, "export const ACTION_ICONS = ", "{", "}")))
    check(
        f"ACTION_ICONS 覆盖后端全部动作（缺 {sorted(backend_actions - action_icons)}）",
        backend_actions <= action_icons,
    )

    # 图标名必须真在 AppIcon 表里：写错不报错，只会静默回退成 sprout
    names = set(re.findall(r": '([\w-]+)'", js_block(audit, "export const ACTION_ICONS = ", "{", "}")))
    missing = [n for n in sorted(names) if not re.search(rf"^\s*'?{re.escape(n)}'?:\s*\[", icon_src, re.M)]
    check(f"动作图标名都在 AppIcon 表里（缺 {missing}）", not missing)


# ---------------------------------------------------------------- C 页面层

def check_page(browser):
    print("\n== C. 页面层（Playwright）==")

    ui = register("pwdC")
    UIDS.append(ui["uid"])
    ui_token = ui["token"]

    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = attach(ctx.new_page())
    inject_login(page, ui_token, ui["user"])
    page.goto(f"{FRONT}/security?tab=password", wait_until="networkidle")
    page.wait_for_selector("[data-test='password-panel']", timeout=10000)
    page.wait_for_timeout(400)

    # C1 第三个 tab 与副标题
    check("URL 上的 tab=password 直接落到改密面板", page.locator("[data-test='password-panel']").is_visible())
    tabs = [
        page.locator("[data-test='security-tab-security']").count(),
        page.locator("[data-test='security-tab-activity']").count(),
        page.locator("[data-test='security-tab-password']").count(),
    ]
    check(f"三个分段控件都在（{tabs}）", tabs == [1, 1, 1])
    check("副标题换成了改密口径", "定期更换密码" in page.locator("[data-test='security-subtitle']").inner_text())

    for anchor in ("pw-old", "pw-next", "pw-confirm", "pw-submit"):
        check(f"表单锚点存在：{anchor}", page.locator(f"[data-test='{anchor}']").count() == 1)

    # C2 输入框上界 = 服务端上界（前后端口径直接断言）
    for anchor in ("pw-next", "pw-confirm"):
        got = page.get_attribute(f"[data-test='{anchor}']", "maxlength")
        check(f"{anchor} 的 maxlength 与服务端上界一致（{got}）", got == str(PW_MAX))

    # 图标尺寸自检：写错尺寸类不会报错，只会把 SVG 撑成容器大小
    box = page.locator("[data-test='password-panel']").locator("svg").first.bounding_box()
    check(f"面板内图标尺寸正常（宽 {box['width'] if box else None}）", bool(box) and box["width"] <= 24)

    # C3 本地校验：两次不一致 → 就地红字、不发请求、不弹全局提示
    page.fill("[data-test='pw-old']", WRONG_CURRENT)
    page.fill("[data-test='pw-next']", UI_PW)
    page.fill("[data-test='pw-confirm']", UI_PW + "x")
    page.click("[data-test='pw-submit']")
    page.wait_for_timeout(400)
    check("两次输入不一致 → 就地红字", page.locator("[data-test='pw-error-confirm']").is_visible())
    check("本地校验失败不弹全局提示", page.locator("[data-test='toast-error']").count() == 0)

    # C4 服务端拒绝（当前密码错）→ 就地红字，而不是全局提示
    page.fill("[data-test='pw-confirm']", UI_PW)
    page.click("[data-test='pw-submit']")
    try:
        page.wait_for_selector("[data-test='pw-error-form']", timeout=8000)
        err = page.locator("[data-test='pw-error-form']").inner_text().strip()
    except Exception:  # noqa: BLE001 - 探针绝不抛异常：失败就是一条可读的 FAIL
        err = ""
    check(f"服务端拒绝的文案就地显示（{err!r}）", "当前密码不正确" in err)
    check("服务端 4xx 不改成全局提示（就地红字约定）", page.locator("[data-test='toast-error']").count() == 0)
    check(f"被拒后仍是登录态（{page.url}）", "/login" not in page.url)

    # C5 改密成功：换令牌、仍是登录态、提示讲清「其他设备要重新登录」
    token_before = page.evaluate("() => localStorage.getItem('token')")
    page.fill("[data-test='pw-old']", PASSWORD)
    page.fill("[data-test='pw-confirm']", UI_PW)
    page.click("[data-test='pw-submit']")
    try:
        page.wait_for_selector("[data-test='toast-success']", timeout=8000)
        ok_text = page.locator("[data-test='toast-success']").inner_text()
    except Exception:  # noqa: BLE001
        ok_text = ""
    check(f"出现成功提示（{ok_text.strip()!r}）", "其他设备" in ok_text)
    page.wait_for_timeout(600)
    token_after = page.evaluate("() => localStorage.getItem('token')")
    check(
        "本地令牌已换成新的（否则下一次请求就会 401）",
        bool(token_after) and token_after != token_before,
    )
    check(f"改密后仍在登录态（{page.url}）", "/login" not in page.url)

    # 改密前的令牌（API 侧）确实已作废
    status, _ = api_status("/users/me", token=ui_token)
    check(f"页面改密后，改密前那张令牌立即失效（实际 {status}）", status == 401)

    # C6 改密后当前设备继续可用（新令牌真的被用上了）
    page.locator("[data-test='security-tab-activity']").click()
    try:
        page.wait_for_selector("[data-test='log-row']", timeout=8000)
    except Exception:  # noqa: BLE001
        pass
    check(
        f"改密后当前设备仍能拉取受保护接口（{page.url}）",
        "/login" not in page.url and page.locator("[data-test='log-row']").count() >= 1,
    )

    # C7 窄屏不得横向溢出
    for width, height, name in [(320, 720, "tiny"), (360, 780, "small"), (390, 844, "mobile")]:
        page.set_viewport_size({"width": width, "height": height})
        page.goto(f"{FRONT}/security?tab=password", wait_until="networkidle")
        page.wait_for_timeout(450)
        over = page.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
        check(f"{name} {width}px 无横向溢出（多出 {over}px）", over <= 1)

    # C8 深浅色截图
    SHOTS.mkdir(parents=True, exist_ok=True)
    page.set_viewport_size({"width": 1440, "height": 900})
    for scheme in ("light", "dark"):
        page.emulate_media(color_scheme=scheme)
        page.goto(f"{FRONT}/security?tab=password", wait_until="networkidle")
        page.wait_for_timeout(700)
        page.locator("[data-test='password-panel']").scroll_into_view_if_needed()
        page.wait_for_timeout(1200)
        page.screenshot(path=str(SHOTS / f"security-password-{scheme}.png"))
    page.emulate_media(color_scheme="light")
    check("深浅色截图已生成", (SHOTS / "security-password-dark.png").exists())

    ctx.close()


# ---------------------------------------------------------------- 主流程

def main():
    check_api()
    check_sources()

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            check_page(browser)
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
                "| 残留安全事件",
                sql_one(f"SELECT COUNT(*) FROM security_events WHERE target_user_id IN ({ph})"),
            )
    finish()
