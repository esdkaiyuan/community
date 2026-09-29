# -*- coding: utf-8 -*-
"""安全事件（被拒的尝试）端到端验证。

补的是上一轮明确留下的缺口：**「期望被拒」的路径不留痕** —— 注册被拒、登录失败、
令牌无效，这些恰恰是攻击（撞库 / 账号枚举 / 伪造令牌）最直接的证据，此前一条都不记。

设计要点（断言就是围绕它们写的）：
  * 与 activity_logs 分开一张表：那边记「谁做成了什么」，这边记「有人尝试但没成功」，
    大多没有身份，且需要聚合。
  * **绝不记密码**（任何形态）；**账号只存脱敏形态**。
  * 按 fingerprint + 时间窗口**聚合**：同一来源对同一目标反复失败合并成一条带次数的行，
    否则暴力破解的「海量重复」会直接把日志变成噪音。
  * 只记**真正可疑**的令牌失败：缺 token（未登录）与过期 token（会话到期）不记。

分段：
  A 登录失败留痕（身份、脱敏、ip/ua/path、无明文）
  B 聚合（窗口内合并 / 不同账号分行 / 窗口外新行 / 并发不丢计数）
  C 注册被拒留痕（各条拒绝路径）+ 拒绝时不建号
  D 令牌被拒留痕（伪造 / 篡改记，缺失 / 过期 / optionalAuth 不记）
  E 只读接口 GET /logs/me/security（本人可见、他人不可见、筛选、分页健壮性）
  F 成功路径**不写**安全事件（只进操作日志），防「两张表互相串味」
  G 全表完整性：没有任何一行含 CR/LF/ESC/NUL/TAB

跑法：在仓库根目录执行  python scripts/verify_security_events.py
"""
import os
import re
import shutil
import subprocess
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _verify_common import (  # noqa: E402
    PASSWORD,
    TS,
    api,
    api_status,
    check,
    cleanup_security_events,
    cleanup_users,
    count_dirty_security_text,
    finish,
    register,
    security_event_rows,
    sql,
    sql_one,
)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.join(REPO, "backend")
NODE = (
    os.environ.get("NODE_BIN")
    or shutil.which("node")
    or r"C:\Users\28916\.workbuddy\binaries\node\versions\22.22.2-2\node.exe"
)

LOGIN_EVENT = "auth.login.rejected"
REG_EVENT = "auth.register.rejected"
TOKEN_EVENT = "auth.token.rejected"
LOCAL_IPS = ("127.0.0.1", "::1", "::ffff:127.0.0.1")

# 造数登记（模块级：任何一步炸了都要能清干净）
UIDS = []

# 英文技术原文：安全事件的 reason 里出现任何一个都算「把框架错误原文甩出来了」
EN_TECH = ("must be", "Cannot", "cannot", "Unexpected", "position", "invalid", "Sequelize", "ER_", "SQL")


# ---- 与后端 maskAccount 同口径的期望值（前端/脚本侧自己算一遍，而不是抄一份写死的常量）----
def mask_email(email):
    local, _, domain = email.rpartition("@")
    dot = domain.rfind(".")
    tld = domain[dot:] if dot > 0 else ""
    return f"{local[0]}***@{domain[0]}***{tld}"


def mask_name(name):
    return f"{name[0]}***"


def se_count(where="1"):
    return int(sql_one(f"SELECT COUNT(*) FROM security_events WHERE {where}"))


def se_occ_sum(where="1"):
    return int(sql_one(f"SELECT COALESCE(SUM(occurrences),0) FROM security_events WHERE {where}"))


def table_contains(needle):
    """整张表（所有文本列）里是否出现过这个字符串 —— 用来证明明文没落库。"""
    esc = needle.replace("'", "''")
    return int(
        sql_one(
            "SELECT COUNT(*) FROM security_events WHERE CONCAT_WS('|', event, reason, account, ip, "
            f"user_agent, path, method) LIKE '%{esc}%'"
        )
    )


def login_raw(email, password):
    """打一次登录（**绝不走 register helper**，避免污染账号登记表）"""
    return api_status("/users/login", {"email": email, "password": password})


def main():
    print("== A. 登录失败留痕 ==")
    # 先用一次**成功**的注册拿到真实账号（成功路径不该写安全事件，见 F 段）
    a = register("secA")
    UIDS.append(a["uid"])
    a_email = f"{a['username']}@example.com"
    check("前置：临时账号注册成功（成功路径）", bool(a["token"]))

    base_login_rows = se_count(f"event='{LOGIN_EVENT}'")
    code, body = login_raw(a_email, "wrong-password-1")
    check("密码错误 -> 401", code == 401)
    check("对外文案不区分「账号不存在」与「密码错误」", body.get("message") == "邮箱或密码错误")

    rows = security_event_rows(f"event='{LOGIN_EVENT}' AND target_user_id={a['uid']}")
    check("登录失败落了一条安全事件", len(rows) == 1)
    row = rows[0] if rows else {}
    check("事件类型是 auth.login.rejected", row.get("event") == LOGIN_EVENT)
    check("记下了被瞄准的账号ID（有人正在打这个账号）", row.get("target_user_id") == str(a["uid"]))
    check("账号列是脱敏形态", row.get("account") == mask_email(a_email))
    check("账号列不含明文邮箱", a_email not in row.get("account", ""))
    check("reason 是中文人话", row.get("reason") == "邮箱或密码错误")
    check("记下了来源 IP", row.get("ip") in LOCAL_IPS)
    check("记下了接口路径与方法", row.get("path") == "/api/users/login" and row.get("method") == "POST")
    check("首次出现 occurrences 为 1", row.get("occurrences") == 1)
    check("多了一条（基线之上正好 +1）", se_count(f"event='{LOGIN_EVENT}'") == base_login_rows + 1)
    check("整表不含明文邮箱", table_contains(a_email) == 0)
    check("整表不含密码明文（任何形态都不该落库）", table_contains("wrong-password-1") == 0)

    print("== B. 聚合：同一来源反复失败合并成一条带次数的行 ==")
    for i in range(4):
        login_raw(a_email, f"wrong-password-{i + 2}")
    rows = security_event_rows(f"event='{LOGIN_EVENT}' AND target_user_id={a['uid']}")
    check("窗口内重复失败**不新增行**（否则暴力破解会把日志刷爆）", len(rows) == 1)
    check("重复失败累加到 occurrences", rows and rows[0]["occurrences"] == 5)
    check("reason 仍是最新一次的原因", rows and rows[0]["reason"] == "邮箱或密码错误")

    last_seen = sql_one(f"SELECT last_seen_at FROM security_events WHERE id = {rows[0]['id']}")
    created = sql_one(f"SELECT created_at FROM security_events WHERE id = {rows[0]['id']}")
    check("last_seen_at 已被刷新（不早于创建时间）", last_seen >= created[:19].replace(" ", " ") or last_seen[:19] >= created[:19])

    # 不同账号 -> 不同聚合键
    b = register("secB")
    UIDS.append(b["uid"])
    b_email = f"{b['username']}@example.com"
    # 🔥 这两个账号的**脱敏形态是同一个**（`secA…@example.com` 与 `secB…@example.com`
    # 都变成 `s***@e***.com`）—— 正好拿来验「聚合键里有目标账号ID」这条：
    # 少了它，两个账号会被并成一行，且行里的 target_user_id 被覆盖成后一个（日志指错人）。
    check("构造成立：两个账号脱敏后确实碰撞成同一个形态", mask_email(a_email) == mask_email(b_email))

    login_raw(b_email, "wrong-password-b")
    rows_b = security_event_rows(f"event='{LOGIN_EVENT}' AND target_user_id={b['uid']}")
    check("换个账号失败是新的一条（脱敏碰撞也不会并到一起）", len(rows_b) == 1)
    check("新行的 occurrences 从 1 起算", rows_b and rows_b[0]["occurrences"] == 1)
    rows_a = security_event_rows(f"event='{LOGIN_EVENT}' AND target_user_id={a['uid']}")
    check("a 的行没有被 b 的失败污染（目标账号不漂移）",
          len(rows_a) == 1 and rows_a[0]["occurrences"] == 5)

    # 窗口外 -> 新的一条
    a_row_id = rows[0]["id"]
    sql(f"UPDATE security_events SET last_seen_at = NOW() - INTERVAL 20 MINUTE WHERE id = {a_row_id};")
    login_raw(a_email, "wrong-password-after-window")
    rows_after = security_event_rows(f"event='{LOGIN_EVENT}' AND target_user_id={a['uid']}")
    check("窗口外的失败另起一条（不是永远合并成一行）", len(rows_after) == 2)
    newest = [r for r in rows_after if r["id"] != a_row_id]
    check("新行的 occurrences 从 1 起算", newest and newest[0]["occurrences"] == 1)
    check("窗口外的行没有被算进旧行", (rows_after[0]["occurrences"] if rows_after[0]["id"] == a_row_id else 0) == 5)

    # 并发：每次尝试都必须被数到（occurrences 必须是 SQL 层原子自增）
    where = f"event='{LOGIN_EVENT}' AND target_user_id={a['uid']}"
    before_occ = se_occ_sum(where)
    threads = [threading.Thread(target=login_raw, args=(a_email, "wrong-conc-%d" % i)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    after_occ = se_occ_sum(where)
    check("5 个并发失败尝试一次都没丢（原子自增，不是读改写）", after_occ - before_occ == 5)
    distinct_fp = int(sql_one(f"SELECT COUNT(DISTINCT fingerprint) FROM security_events WHERE {where}"))
    check("并发产生的事件仍归一到同一个聚合键", distinct_fp == 1)

    print("== C. 注册被拒留痕 ==")
    users_before = int(sql_one("SELECT COUNT(*) FROM users"))

    # C1 缺字段（账号为 null：连试的是哪个账号都不知道）
    code, body = api_status("/users/register", {})
    check("空 body 注册 -> 400", code == 400)
    c_rows = security_event_rows(f"event='{REG_EVENT}'")
    check("注册被拒也留痕", len(c_rows) == 1)
    check("拿不到账号时 account 为空（而不是硬塞个占位符）", c_rows and c_rows[0]["account"] == "")
    check("reason 是中文人话", c_rows and "必填" in c_rows[0]["reason"])

    # C2 用户名被占（账号枚举/撞名的直接证据）
    code, body = api_status(
        "/users/register",
        {"username": a["username"], "email": f"secc2{TS}@example.com", "password": PASSWORD},
    )
    check("重名注册 -> 409", code == 409)
    c_rows = security_event_rows(f"event='{REG_EVENT}'")
    check("重名注册新增一行（账号标识不同）", len(c_rows) == 2)
    taken = [r for r in c_rows if r["account"] == mask_name(a["username"])]
    check("记下撞上的账号ID（账号枚举的命中记录）", taken and taken[0]["target_user_id"] == str(a["uid"]))
    check("撞名的账号标识也是脱敏的", taken and a["username"] not in taken[0]["account"])

    # C3 密码太短
    weak_name = f"secCw{TS}"
    code, body = api_status(
        "/users/register", {"username": weak_name, "email": f"{weak_name}@example.com", "password": "123"}
    )
    check("密码过短 -> 400", code == 400)
    c_rows = security_event_rows(f"event='{REG_EVENT}'")
    check("密码过短也留痕（独立的账号标识 -> 独立一行）", len(c_rows) == 3)
    weak_row = [
        r for r in c_rows if r["account"] == mask_name(weak_name) and r["target_user_id"] == ""
    ]
    check(
        "拒绝文案里的数字与真实下限一致",
        bool(weak_row) and re.search(r"\d+", weak_row[0]["reason"]).group(0) == "6",
    )

    # C4 用户名净化后不合法（emoji 会被剥掉）—— 与 C1 同为「无账号标识」，按设计合并
    code, body = api_status(
        "/users/register", {"username": "🎯🎯", "email": f"secc4{TS}@example.com", "password": PASSWORD}
    )
    check("emoji 用户名 -> 400（剥完不足 2 字）", code == 400)
    c_rows = security_event_rows(f"event='{REG_EVENT}'")
    check(
        "reason 不进聚合键：同为「无账号标识」的两种原因合并成一条并累加次数",
        len(c_rows) == 3 and c_rows[0]["occurrences"] == 2,
    )

    check("被拒的注册一个账号都没建出来", int(sql_one("SELECT COUNT(*) FROM users")) == users_before)
    check(
        "注册被拒的 reason 全都本地化（没有框架英文原文）",
        all(not any(t in r["reason"] for t in EN_TECH) for r in c_rows),
    )

    print("== D. 令牌被拒留痕 ==")
    token_rows_before = se_count(f"event='{TOKEN_EVENT}'")

    code, body = api_status("/logs/me", token="not.a.jwt")
    check("伪造令牌 -> 401", code == 401)
    t_rows = security_event_rows(f"event='{TOKEN_EVENT}'")
    check("伪造令牌留痕", len(t_rows) == token_rows_before + 1)
    check("令牌事件没有「被瞄准的账号」（攻击者未登录，本就没有身份）",
          t_rows and t_rows[-1]["target_user_id"] == "")
    check("令牌事件的 reason 是中文人话", t_rows and t_rows[-1]["reason"] == "认证令牌无效（签名或格式异常）")
    check("记下了被打的接口", t_rows and t_rows[-1]["path"] == "/api/logs/me")

    # 篡改真实令牌的最后一个字符（签名字节被改）
    tampered = a["token"][:-1] + ("a" if a["token"][-1] != "a" else "b")
    code, _ = api_status("/logs/me", token=tampered)
    check("签名被篡改的令牌 -> 401", code == 401)
    check(
        "篡改令牌与伪造令牌在窗口内合并（同来源同接口 -> 一条带次数的行）",
        se_count(f"event='{TOKEN_EVENT}'") == token_rows_before + 1,
    )

    # path 不同 -> 新的聚合键
    code, _ = api_status("/users/me", token="not.a.jwt")
    check("坏令牌打另一个接口 -> 401", code == 401)
    check("不同接口是不同聚合键（多一行）", se_count(f"event='{TOKEN_EVENT}'") == token_rows_before + 2)

    # query 不该被抄进日志，也不该把聚合键打散
    n_tok = se_count(f"event='{TOKEN_EVENT}'")
    code, _ = api_status("/logs/me?page=1&token=LEAKME", token="not.a.jwt")
    check("带 query 的坏令牌请求 -> 401", code == 401)
    check(
        "query 不进聚合键（同一接口不因参数不同而分裂成多行）",
        se_count(f"event='{TOKEN_EVENT}'") == n_tok,
    )
    paths = [r["path"] for r in security_event_rows(f"event='{TOKEN_EVENT}'")]
    check("路径里不含 query（敏感参数不会被抄进日志）",
          paths and all("LEAKME" not in p and "?" not in p for p in paths))
    check("路径被记成接口本身", paths.count("/api/logs/me") >= 1)

    # ⚠️ 下面三条是「**不记**」的设计断言，和上面同等重要：记错了就是日志洪水
    n_before = se_count()
    code, _ = api_status("/logs/me")
    check("缺令牌 -> 401（正常：用户没登录）", code == 401)
    check("缺令牌**不留痕**（否则每次未登录点收藏都写一行）", se_count() == n_before)

    expired = make_expired_token(a["uid"])
    check("过期令牌生成成功（用与后端同一份 JWT_SECRET）", expired.count(".") == 2)
    code, body = api_status("/logs/me", token=expired)
    check("过期令牌 -> 401", code == 401)
    check("过期令牌**不留痕**（签名是对的，只是会话到期，属正常场景）", se_count() == n_before)

    pid = int(sql_one("SELECT id FROM projects WHERE deleted_at IS NULL ORDER BY id LIMIT 1"))
    code, _ = api_status(f"/projects/{pid}", token="not.a.jwt")
    check("坏令牌打公开接口 -> 200（optionalAuth 静默退化为未登录）", code == 200)
    check("optionalAuth 不留痕（公开页面上一个过期 token 会刷出洪水）", se_count() == n_before)

    print("== E. 只读接口 GET /logs/me/security ==")
    code, body = api_status("/logs/me/security")
    check("未登录 -> 401", code == 401)

    token_rows = api("/logs/me/security", token=a["token"])
    check("本人可读 -> 200", token_rows.get("code") == 200)
    events = (token_rows.get("data") or {}).get("events") or []
    check("能看到针对自己账号的被拒尝试", len(events) >= 2)
    check("事件里含登录失败", any(e["event"] == LOGIN_EVENT for e in events))
    check("事件里含有人拿自己用户名去注册", any(e["event"] == REG_EVENT for e in events))
    check("返回了聚合次数（用于判断强度）", all("occurrences" in e for e in events))
    check("只返回针对本人账号的事件",
          int(sql_one(f"SELECT COUNT(*) FROM security_events WHERE target_user_id = {a['uid']}")) == len(events))
    dumped = str(events)
    check("接口响应里没有明文邮箱", a_email not in dumped)
    check("接口响应里没有密码明文", "wrong-password" not in dumped)
    check("账号在响应里也是脱敏的", all("@example.com" not in (e.get("account") or "") for e in events))

    other = api("/logs/me/security", token=b["token"])["data"]["events"]
    check("别人的 token 看不到针对我的事件（按身份隔离）",
          set(e["id"] for e in other).isdisjoint(set(e["id"] for e in events)))

    filtered = api("/logs/me/security?event=" + LOGIN_EVENT, token=a["token"])["data"]["events"]
    check("按事件类型筛选生效", filtered and all(e["event"] == LOGIN_EVENT for e in filtered))
    code, body = api_status("/logs/me/security?event=../evil", token=a["token"])
    check("非法事件类型 -> 400（明确拒绝，不静默忽略）", code == 400)
    check("非法筛选的文案是中文人话", "不支持" in (body.get("message") or ""))

    code, body = api_status(
        "/logs/me/security?page=99999999999999999999&pageSize=0", token=a["token"]
    )
    check("分页溢出值 / 0 不会把 500 甩给用户", code == 200)
    check("pageSize 兜到合法下界", (body.get("data") or {}).get("pageSize", 0) >= 1)
    check("page 被夹到上界而不是原样拼进 SQL", (body.get("data") or {}).get("page", 0) <= 100000)

    code, body = api_status("/logs/me/security?pageSize=abc", token=a["token"])
    check("非数字 pageSize -> 200（走兜底而不是报错）", code == 200)

    plain = api("/logs/me", token=a["token"])
    check("GET /logs/me（操作日志）没被 /me/security 抢掉路由", plain.get("code") == 200)

    print("== F. 成功路径不写安全事件 ==")
    n_before = se_count()
    c = register("secF")
    UIDS.append(c["uid"])
    code, _ = login_raw(f"{c['username']}@example.com", PASSWORD)
    check("注册 + 登录都成功", code == 200)
    check("成功路径**不写**安全事件（两张表不互相串味）", se_count() == n_before)
    check("但成功注册仍进操作日志（原有能力没被改坏）",
          int(sql_one(f"SELECT COUNT(*) FROM activity_logs WHERE action='user.register' AND user_id={c['uid']}")) == 1)

    print("== G. 全表完整性 ==")
    check("没有任何一行含 CR/LF/ESC/NUL/TAB", count_dirty_security_text() == 0)
    check("没有任何一行的 reason 为空（列是 NOT NULL）",
          int(sql_one("SELECT COUNT(*) FROM security_events WHERE reason IS NULL OR reason = ''")) == 0)
    check("没有任何一行的 fingerprint 为空",
          int(sql_one("SELECT COUNT(*) FROM security_events WHERE fingerprint IS NULL OR fingerprint = ''")) == 0)
    check("occurrences 全部 >= 1",
          int(sql_one("SELECT COUNT(*) FROM security_events WHERE occurrences < 1")) == 0)


def make_expired_token(user_id):
    """用**与后端同一份 .env / JWT_SECRET** 签一个已过期的令牌。

    ⚠️ 必须用同一个密钥：jsonwebtoken 先验签名再看 exp，密钥不对抛的是
    JsonWebTokenError（会被当成「伪造」留痕），就测不到「过期不留痕」这条了。
    """
    js = (
        "const jwt=require('jsonwebtoken');"
        "require('dotenv').config();"
        "console.log(jwt.sign({userId:%d}, process.env.JWT_SECRET, {expiresIn:'-10s'}));" % user_id
    )
    proc = subprocess.run(
        [NODE, "-e", js], cwd=BACKEND, capture_output=True, encoding="utf-8", errors="replace"
    )
    return (proc.stdout or "").strip()


def cleanup():
    """清理：security_events 不挂外键，且被拒的尝试是**任何脚本**都会写进去的，
    必须显式清（按来源 IP —— 本机验证流量一律来自 localhost）。"""
    if UIDS:
        cleanup_users(UIDS)
    cleanup_security_events()


if __name__ == "__main__":
    try:
        main()
    finally:
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
                sql_one("SELECT COUNT(*) FROM security_events WHERE ip IN ('127.0.0.1','::1','::ffff:127.0.0.1') OR ip IS NULL"),
            )
    finish()
