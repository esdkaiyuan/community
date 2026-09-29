"""操作日志（审计留痕）端到端验证。

覆盖五件事：
  A~E  五条内容写路径（发布 / 编辑 / 删除项目、发表 / 删除评论）是否真的落库，
       并且**落库的内容是净化过的**（CRLF 伪造、ANSI、RLO、NUL、超长）
  F    只读接口 GET /logs/me：仅本人可见、筛选、分页、非法筛选报 400、未登录 401
  G~H  设计断言：日志表**不挂外键**，所以删除项目 / 硬删用户之后证据仍在
  I    动作白名单：未知 action 被拒绝且不抛异常（走 node 子进程直接调服务）
  J    留存清理脚本（真跑进程，断言退出码 + 真实副作用）
  K    **username 列不再是被净化链遗忘的那一列**：直接改库造一条脏数据（绕开服务层），
       再触发一次写日志，断言日志列没被污染 —— 验的是「日志完整性不依赖上游字段干净」
  L    身份字段归一化（注册与改名共用一个口径）+ 注册 / 资料变更的审计留痕

跑法：在仓库根目录执行  python scripts/verify_activity_logs.py
"""
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _verify_common import (  # noqa: E402
    PASSWORD,
    TS,
    api,
    api_status,
    check,
    cleanup_project,
    cleanup_users,
    create_project,
    finish,
    register,
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

# 造数登记（模块级，保证任何一步炸了都能清干净）
UIDS = []  # 传给 cleanup_users；H 段会把已删除的用户从中摘掉
ALL_UIDS = []  # 只增不减：日志清理按它来，否则「已删用户」的日志永远清不掉
PIDS = []

# 服务层白名单的全部取值（journal 里出现白名单外的动作 = 有人在绕过 record()）
KNOWN_ACTIONS = (
    "project.create",
    "project.update",
    "project.delete",
    "comment.create",
    "comment.delete",
    "user.register",
    "user.profile.update",
)

# 载荷：把四类注入面塞进一个标题里
CRLF_TITLE = "注入标题\r\n[FATAL][auth] admin 登录成功"
# 载荷：ANSI 彩色 + CRLF 伪造行 + RLO 方向控制 + 零宽 + NUL
DIRTY_CONTENT = "危险\u001b[31m红字\u001b[0m\r\n[DONE] 伪造行\u202e反向\u200b零宽\u0000NUL 结束"
LONG_CONTENT = "长文本前缀" + "很长的内容" * 60  # 远超 60 字的摘要预览上限

# 日志里绝不允许出现的字符（换行 / 控制字符 / 方向控制 / 零宽）
FORBIDDEN = ["\n", "\r", "\u001b", "\u202e", "\u200b", "\u0000", "\u2028", "\u2029"]


def find_log(logs, action, target_id=None):
    for item in logs:
        if item["action"] != action:
            continue
        if target_id is None or item["targetId"] == target_id:
            return item
    return None


def dirty_chars(text):
    return [c for c in FORBIDDEN if c in text]


def main():
    a = register("logA")
    UIDS.append(a["uid"])
    ALL_UIDS.append(a["uid"])
    b = register("logB")
    UIDS.append(b["uid"])
    ALL_UIDS.append(b["uid"])

    # ---------------- A. 发布内容：CRLF 注入标题 + body 里的 req 伪造 ----------------
    print("== A. 发布项目（CRLF 注入标题 / body 伪造 req）==")
    body = {
        "title": CRLF_TITLE,
        "description": "这是一条用于操作日志验证的临时项目描述，验证结束后会被完整清理。",
        "categoryId": 1,
        "tags": ["日志验证", "安全"],
        # 客户端伪造 req：如果控制器里的展开顺序写反了，来源 IP 就会被顶掉
        "req": {"ip": "1.2.3.4", "headers": {"user-agent": "ForgeBot/1.0"}},
    }
    resp = api("/projects", body, token=a["token"])
    pid = resp["data"]["id"]
    PIDS.append(pid)

    # 断言用 `.get()` + `bool(...)` 兜底：日志根本没写时，下面每一条都必须**变红**，
    # 而不是因为取不到键就整段静默跳过（那样「红」就只剩一条，说服力不足）
    logs = api("/logs/me", token=a["token"])["data"]["logs"]
    created = find_log(logs, "project.create", pid) or {}
    detail = created.get("detail") or {}
    summary = created.get("summary") or ""
    check("发布项目产生一条 project.create 日志", bool(created))
    check("摘要里没有换行（CRLF 被压平）", bool(summary) and not dirty_chars(summary))
    check("摘要保留了原来的文字（不是被整段丢掉）", "注入标题" in summary)
    check("标题里的伪造行仍在同一行内", "[FATAL]" in summary)
    check("摘要长度不超过列宽 255", bool(summary) and len(summary) <= 255)
    check("detail 键恰好是白名单三个", sorted(detail.keys()) == ["categoryId", "tags", "title"])
    check("detail.tags 数组原样保留", detail.get("tags") == ["日志验证", "安全"])
    check("detail 里的标题同样被净化", bool(detail.get("title")) and not dirty_chars(detail["title"]))
    check("body 里的 req 顶不掉真身：来源 IP 不是伪造值",
          bool(created.get("ip")) and created.get("ip") != "1.2.3.4")
    check("body 里的 req 顶不掉真身：UA 仍是真实客户端",
          str(created.get("userAgent") or "").startswith("Python-urllib"))
    check("来源 IP 是合法的本机地址", created.get("ip") in ("::1", "127.0.0.1", "::ffff:127.0.0.1"))
    check("动作值在服务层白名单内", created.get("action") == "project.create")
    check("目标类型与目标 ID 正确",
          created.get("targetType") == "project" and created.get("targetId") == pid)

    # 写日志是 await 的（不是 fire-and-forget），所以接口返回时库里必须已经有了
    db_count = int(sql_one(f"SELECT COUNT(*) FROM activity_logs WHERE action='project.create' AND target_id={pid}"))
    check("接口返回时日志已落库（写入是同步等待的）", db_count == 1)

    # ---------------- B. 评论：把四类注入面一次塞进去 ----------------
    print("== B. 发表评论（ANSI / CRLF / RLO / 零宽 / NUL）==")
    c1 = api(f"/projects/{pid}/comments", {"content": DIRTY_CONTENT}, token=b["token"])["data"]["comment"]

    logs = api("/logs/me", token=b["token"])["data"]["logs"]
    c_log = find_log(logs, "comment.create", c1["id"]) or {}
    c_detail = c_log.get("detail") or {}
    c_summary = c_log.get("summary") or ""
    check("发言产生一条 comment.create 日志", bool(c_log))
    check("摘要里没有任何禁止字符", bool(c_summary) and not dirty_chars(c_summary))
    check("ANSI 转义被整体摘除（不是留下 [31m）", "\u001b" not in c_summary and "[31m" not in c_summary)
    check("摘要里能看到用户原本写的字", "危险" in c_summary and "红字" in c_summary)
    check("伪造行被压进同一行", "[DONE] 伪造行" in c_summary)
    check("RLO 被移除，正文字符保持原顺序", "反向" in c_summary)
    check("detail 键恰好是白名单三个", sorted(c_detail.keys()) == ["isReply", "preview", "projectTitle"])
    check("首条评论 isReply 为 false", c_detail.get("isReply") is False)
    check("detail.preview 同样被净化", bool(c_detail.get("preview")) and not dirty_chars(c_detail["preview"]))
    check("摘要带了项目标题（人读得懂在哪儿评的）", bool(c_detail.get("projectTitle")))

    # 回复：isReply 翻成 true，并且挂在同一条项目上
    c1b = api(f"/projects/{pid}/comments", {"content": "这是回复，用来验证 isReply", "parentId": c1["id"]}, token=b["token"])["data"]["comment"]
    logs = api("/logs/me", token=b["token"])["data"]["logs"]
    r_log = find_log(logs, "comment.create", c1b["id"]) or {}
    check("回复被判为 isReply=true", (r_log.get("detail") or {}).get("isReply") is True)

    # ---------------- C. 超长内容：截断且可见 ----------------
    print("== C. 超长评论（存储放大防护）==")
    c2 = api(f"/projects/{pid}/comments", {"content": LONG_CONTENT}, token=b["token"])["data"]["comment"]
    logs = api("/logs/me", token=b["token"])["data"]["logs"]
    long_log = find_log(logs, "comment.create", c2["id"]) or {}
    long_detail = long_log.get("detail") or {}
    long_summary = long_log.get("summary") or ""
    check("超长评论也留了痕", bool(long_log))
    check("摘要被截断到 255 以内", bool(long_summary) and len(long_summary) <= 255)
    check("截断处有省略号（不是静默丢弃）", long_summary.endswith("…"))
    check("内容预览被截到 60 字以内", bool(long_detail.get("preview")) and len(long_detail["preview"]) <= 60)
    check("预览同样以省略号收尾", str(long_detail.get("preview") or "").endswith("…"))

    # ---------------- D. 编辑项目：只记真正改动的字段 ----------------
    print("== D. 编辑项目 ==")
    api(f"/projects/{pid}", {"title": "改过的标题\r\n[WARN] 又一条伪造行"}, token=a["token"], method="PUT")
    logs = api("/logs/me", token=a["token"])["data"]["logs"]
    upd = find_log(logs, "project.update", pid) or {}
    upd_changed = (upd.get("detail") or {}).get("changed") or []
    check("编辑产生 project.update 日志", bool(upd))
    check("changed 里记录了 title", "title" in upd_changed)
    check("changed 里没有未改动的字段", "description" not in upd_changed)
    check("编辑摘要同样无禁止字符", bool(upd.get("summary")) and not dirty_chars(upd["summary"]))

    # 空 PUT（什么都没改）不应留下一堆噪音日志
    before = int(sql_one(f"SELECT COUNT(*) FROM activity_logs WHERE action='project.update' AND target_id={pid}"))
    api(f"/projects/{pid}", {"title": "改过的标题\r\n[WARN] 又一条伪造行"}, token=a["token"], method="PUT")
    after = int(sql_one(f"SELECT COUNT(*) FROM activity_logs WHERE action='project.update' AND target_id={pid}"))
    check("没改动时不写日志（不做无意义留痕）", before == after == 1)

    # ---------------- E. 删除评论 ----------------
    print("== E. 删除评论 ==")
    api(f"/projects/{pid}/comments/{c1['id']}", None, token=b["token"], method="DELETE")
    logs = api("/logs/me", token=b["token"])["data"]["logs"]
    del_log = find_log(logs, "comment.delete", c1["id"]) or {}
    del_summary = del_log.get("summary") or ""
    check("删除评论产生 comment.delete 日志", bool(del_log))
    check("删除摘要里留下了「删的是哪条」", "危险" in del_summary)
    check("删除摘要无禁止字符", bool(del_summary) and not dirty_chars(del_summary))

    # ---------------- F. 只读接口 ----------------
    print("== F. GET /logs/me 的隔离、筛选与分页 ==")
    data = api("/logs/me", token=b["token"])["data"]
    db_b = int(sql_one(f"SELECT COUNT(*) FROM activity_logs WHERE user_id={b['uid']}"))
    check("返回条数与库内该用户的条数一致", data["total"] == db_b)
    check("日志按时间倒序（最新的在前）", [x["id"] for x in data["logs"]] == sorted([x["id"] for x in data["logs"]], reverse=True))
    check("所有条目都属于自己（动作白名单内）",
          all(x["action"] in KNOWN_ACTIONS for x in data["logs"]))

    # 隔离：B 的日志里不该出现 A 对项目的编辑/删除动作
    check("看不到别人的日志（无 project.update 之外的越权数据）",
          not any(x["action"] == "project.update" for x in data["logs"]))

    filtered = api("/logs/me?action=comment.create", token=b["token"])["data"]
    check("按 action 筛选生效", filtered["total"] > 0 and all(x["action"] == "comment.create" for x in filtered["logs"]))

    scoped = api(f"/logs/me?projectId={pid}", token=b["token"])["data"]
    check("按项目筛选生效", scoped["total"] > 0 and all(x["projectId"] == pid for x in scoped["logs"]))

    status, body = api_status("/logs/me?action=evil.drop_table", token=b["token"])
    check("非法筛选值返回 400（不是静默忽略）", status == 400)
    check("非法筛选的文案是人话", status == 400 and "不支持" in json.dumps(body, ensure_ascii=False))

    status, _ = api_status("/logs/me")
    check("未登录访问日志返回 401", status == 401)

    p1 = api("/logs/me?pageSize=2&page=1", token=b["token"])["data"]
    p2 = api("/logs/me?pageSize=2&page=2", token=b["token"])["data"]
    check("分页每页条数受限", len(p1["logs"]) <= 2 and len(p2["logs"]) <= 2)
    overlap = {x["id"] for x in p1["logs"]} & {x["id"] for x in p2["logs"]}
    check("相邻两页没有重复条目", not overlap)

    # ---------------- G. 删除项目后日志仍在 ----------------
    print("== G. 删除项目（日志必须活下来）==")
    logs_before = int(sql_one(f"SELECT COUNT(*) FROM activity_logs WHERE project_id={pid}"))
    api(f"/projects/{pid}", None, token=a["token"], method="DELETE")
    logs_after = int(sql_one(f"SELECT COUNT(*) FROM activity_logs WHERE project_id={pid}"))
    check("删除项目的动作本身被记录", logs_after == logs_before + 1)
    deleted = api("/logs/me", token=a["token"])["data"]["logs"]
    d_log = find_log(deleted, "project.delete", pid) or {}
    check("删除日志里保留了项目标题快照", "标题" in (d_log.get("summary") or ""))
    check("项目已被删除但日志仍可读", api("/logs/me", token=a["token"])["data"]["total"] > 0)

    # ---------------- H. 硬删用户后日志仍在（不挂外键的设计证明） ----------------
    print("== H. 硬删用户（审计证据不随账号消失）==")
    # 这一段刻意**不用** cleanup_project / cleanup_users：它们会顺手清掉日志，
    # 而那正是本段要证明「不会发生」的事。改成生产里真会发生的裸删语句。
    for stmt in (
        f"DELETE FROM comment_likes WHERE comment_id IN (SELECT id FROM project_comments WHERE project_id = {pid})",
        f"DELETE FROM notifications WHERE project_id = {pid}",
        f"DELETE FROM project_comments WHERE project_id = {pid}",
        f"DELETE FROM project_participants WHERE project_id = {pid}",
        f"DELETE FROM project_likes WHERE project_id = {pid}",
        f"DELETE FROM project_favorites WHERE project_id = {pid}",
        f"DELETE FROM projects WHERE id = {pid}",
    ):
        sql(stmt + ";")
    PIDS.remove(pid)
    survivors = int(sql_one("SELECT COUNT(*) FROM activity_logs WHERE user_id IN (%d, %d)" % (a["uid"], b["uid"])))
    # 9 条的构成（每一条都对应一次真实写操作，少一条就说明有写路径悄悄不记了）：
    #   A：user.register + project.create + project.update + project.delete = 4
    #   B：user.register + 3 条 comment.create + comment.delete           = 5
    check("硬删项目行后日志依旧存在（9 条一条不少）", survivors == 9)
    sql(f"DELETE FROM users WHERE id = {a['uid']};")
    UIDS.remove(a["uid"])
    still = int(sql_one("SELECT COUNT(*) FROM activity_logs WHERE user_id = %d" % a["uid"]))
    check("硬删用户后其日志仍然存在（未挂外键、未级联）", still == 4)
    check("被删用户的日志里保留了名称快照", int(sql_one(
        "SELECT COUNT(*) FROM activity_logs WHERE user_id = %d AND username IS NOT NULL" % a["uid"])) == still)

    # ---------------- I. 动作白名单与空摘要兜底（直接调服务） ----------------
    print("== I. 动作白名单 / 空摘要兜底 ==")
    # 探针自清：这条是「净化后为空」的构造数据，不该留在库里。让它自己删，
    # 比在 Python 侧按文案匹配稳 —— 净化规则一旦被临时改动，存的就不是
    # '(无摘要)' 了，按文案匹配会静默漏掉（实测踩过）。
    node_code = (
        "const s=require('./src/services/activityLog.service');"
        "const {ActivityLog,sequelize}=require('./src/models');"
        "(async()=>{"
        "const bad=await s.record({action:'evil.inject',userId:1,summary:'x',targetType:'project'});"
        "console.log('BAD:'+(bad===null?'REJECTED':'WROTE'));"
        "const empty=await s.record({action:'project.create',userId:1,summary:'\\u0000\\u0001',targetType:'project'});"
        "console.log('EMPTY:'+(empty&&empty.summary==='(无摘要)'?'FALLBACK':'NOPE'));"
        "if(empty){console.log('EMPTYID:'+empty.id);await ActivityLog.destroy({where:{id:empty.id}})}"
        "await sequelize.close()})()"
        ".catch(async e=>{console.log('THREW:'+e.message);await sequelize.close()})"
    )
    proc = subprocess.run(
        [NODE, "-e", node_code], cwd=BACKEND, capture_output=True, encoding="utf-8", errors="replace"
    )
    out = proc.stdout or ""
    check("未知动作返回 null（被拒绝）", "BAD:REJECTED" in out)
    check("未知动作不抛异常（不会带崩业务）", proc.returncode == 0 and "THREW" not in out)
    check("未知动作没有落库", int(sql_one("SELECT COUNT(*) FROM activity_logs WHERE action='evil.inject'")) == 0)
    check("摘要净化后为空时落到兜底文案（列是 NOT NULL）", "EMPTY:FALLBACK" in out)

    probe_id = re.search(r"EMPTYID:(\d+)", out)
    check("探针留下了可清理的行号", probe_id is not None)
    check("探针把自己造的行删掉了（不留垃圾）",
          probe_id is not None and sql_one("SELECT COUNT(*) FROM activity_logs WHERE id = %s" % probe_id.group(1)) == "0")

    # ---------------- J. 留存清理脚本（真跑进程，断言退出码 + 真实副作用） ----------------
    print("== J. 留存清理脚本 ==")
    sql("INSERT INTO activity_logs (action, target_type, summary, created_at) "
        "VALUES ('comment.create', 'comment', '过期日志_探针', DATE_SUB(NOW(), INTERVAL 10 DAY));")
    sql("INSERT INTO activity_logs (action, target_type, summary, created_at) "
        "VALUES ('comment.create', 'comment', '新日志_探针', NOW());")
    probe_rows = "SELECT COUNT(*) FROM activity_logs WHERE summary LIKE '%\\_探针'"

    proc = subprocess.run(
        [NODE, "scripts/prune-activity-logs.js", "--days=1"],
        cwd=BACKEND, capture_output=True, encoding="utf-8", errors="replace"
    )
    check("干跑退出码为 0", proc.returncode == 0)
    check("干跑报告了 1 条超期", "超出留存期 1 条" in (proc.stdout or ""))
    check("干跑只报告、不删除", sql_one(probe_rows) == "2")

    proc = subprocess.run(
        [NODE, "scripts/prune-activity-logs.js", "--apply", "--days=1"],
        cwd=BACKEND, capture_output=True, encoding="utf-8", errors="replace"
    )
    check("--apply 退出码为 0", proc.returncode == 0)
    check("超出留存期的日志被删除", sql_one("SELECT COUNT(*) FROM activity_logs WHERE summary = '过期日志_探针'") == "0")
    check("留存期内的日志一条没动", sql_one("SELECT COUNT(*) FROM activity_logs WHERE summary = '新日志_探针'") == "1")

    proc = subprocess.run(
        [NODE, "scripts/prune-activity-logs.js", "--days=0"],
        cwd=BACKEND, capture_output=True, encoding="utf-8", errors="replace"
    )
    check("非法参数（--days=0）退出码为 2", proc.returncode == 2)


    # ---------------- K. 日志 username 列：堵住净化旁路 ----------------
    print("== K. username 列不再是被净化链遗忘的那一列 ==")
    # 这一段刻意**绕开服务层**去验：新代码已在注册 / 改名时归一化，正常路径下脏用户名
    # 根本进不了库。所以直接改库造一条「历史遗留 / 绕过服务写进来」的脏数据，再触发一次
    # 写日志 —— 验的是防御纵深本身：**日志列的完整性不能依赖上游字段干净**。
    # 用 UNHEX 构造而不是写 'a\r\nFAKE'：MySQL 字符串字面量会解释反斜杠转义，从 Python 里
    # 拼进去要过两层转义，极易绕晕；HEX 没有歧义。
    kd = register("logKD")
    UIDS.append(kd["uid"])
    ALL_UIDS.append(kd["uid"])
    sql(f"UPDATE users SET username = UNHEX('610D0A46414B45') WHERE id = {kd['uid']};")  # a\r\nFAKE
    check("脏用户名已写进库（构造成功）",
          sql_one(f"SELECT HEX(username) FROM users WHERE id = {kd['uid']}") == "610D0A46414B45")

    kd_pid = create_project(kd["token"], "脏用户名探针项目")
    PIDS.append(kd_pid)

    snap = sql_one(f"SELECT username FROM activity_logs WHERE user_id = {kd['uid']} AND action='project.create'")
    snap_hex = sql_one(f"SELECT HEX(username) FROM activity_logs WHERE user_id = {kd['uid']} AND action='project.create'")
    check("日志 username 列里没有换行（CRLF 没跟着进去）",
          bool(snap_hex) and "0D" not in snap_hex.upper() and "0A" not in snap_hex.upper())
    check("日志 username 列无任何禁止字符", bool(snap) and not dirty_chars(snap))
    check("CRLF 被压成空格、原文仍可读（不是整段丢掉）", snap == "a FAKE")
    check("净化只发生在日志层：库里的账号名依旧是脏的（没顺手改用户数据）",
          sql_one(f"SELECT HEX(username) FROM users WHERE id = {kd['uid']}") == "610D0A46414B45")

    # ---------------- L. 身份字段归一化（注册与改名共用同一口径） ----------------
    print("== L. 用户名归一化 ==")
    seq = [0]

    def reg_raw(uname):
        """注册一次。**无论断言期望成功还是失败，都把真建出来的账号登记进清理列表** ——
        期望「被拒」的用例在旧实现下会真的建号（实测泄漏 2 个），只登记成功路径是不够的。"""
        seq[0] += 1
        code, body = api_status(
            "/users/register",
            {"username": uname, "email": f"norm{TS}x{seq[0]}@example.com", "password": PASSWORD},
            method="POST",
        )
        uid = ((body.get("data") or {}).get("user") or {}).get("id")
        if uid:
            UIDS.append(uid)
            ALL_UIDS.append(uid)
        return code, body

    def reg_ok(label, uname, expected):
        code, body = reg_raw(uname)
        check(f"{label}：注册成功（带脏字符也能建号 = 漏网）", code == 201)
        # 一律用 .get 取键：旧实现里字段不存在时**这一条变红**，而不是 KeyError 把
        # 整段后续断言全跳过（那样「红」就只剩一条，看不出覆盖面）
        check(f"{label}：库里存的是净化后的值 {expected!r}",
              ((body.get("data") or {}).get("user") or {}).get("username") == expected)
        check(f"{label}：响应 adjusted 为 true（不做静默修改）", (body.get("data") or {}).get("adjusted") is True)

    reg_ok("CRLF 伪造", "a\r\nFAKE" + TS, "aFAKE" + TS)
    reg_ok("RLO 方向控制", "b\u202eREV" + TS, "bREV" + TS)
    reg_ok("emoji 开头", "\U0001F3AF" + TS + "ab", TS + "ab")

    # register 原来完全不 trim、updateProfile 会 trim，同一个值两条路径两种结果
    code, body = reg_raw("  " + TS + "x ")
    stored = ((body.get("data") or {}).get("user") or {}).get("username")
    check("首尾空白被收敛（注册与改名终于一个口径）", code == 201 and stored == TS + "x")
    check("只去空白不算「非法字符被移除」（adjusted 为 false，不给无意义提示）",
          code == 201 and (body.get("data") or {}).get("adjusted") is False)

    code, body = reg_raw("\U0001F3AF\U0001F3AF")
    check("纯 emoji 用户名被拒（剥完不足 2 字，不是存成空名字）", code == 400)
    check("拒绝文案是中文人话", code == 400 and "用户名" in json.dumps(body, ensure_ascii=False))
    code, _ = reg_raw("\U0001F3AFa")
    check("剥完只剩 1 字同样被拒（不静默截断成短名）", code == 400)

    # ---------------- L2. 注册与资料变更的审计留痕 ----------------
    print("== L2. 注册 / 资料变更留痕 ==")
    k = register("logK")
    UIDS.append(k["uid"])
    ALL_UIDS.append(k["uid"])
    k_pid = create_project(k["token"], "资料留痕探针项目")
    PIDS.append(k_pid)

    reg_log = find_log(api("/logs/me", token=k["token"])["data"]["logs"], "user.register") or {}
    check("注册产生一条 user.register 日志（审计时间线的起点）", bool(reg_log))
    check("targetType 是 user、targetId 是自己",
          reg_log.get("targetType") == "user" and reg_log.get("targetId") == k["uid"])
    check("detail 只记了 username，没有存 email（少存 PII）",
          sorted((reg_log.get("detail") or {}).keys()) == ["username"])
    check("注册摘要里带了用户名", k["username"] in (reg_log.get("summary") or ""))
    check("快照 == 账号真实用户名（两条净化路径口径一致）",
          sql_one(f"SELECT username FROM activity_logs WHERE user_id = {k['uid']} AND action='user.register'") == k["username"])
    check("新动作已进只读接口的白名单（按它筛选不再 400）",
          api_status("/logs/me?action=user.register", token=k["token"])[0] == 200)

    old_name = k["username"]
    new_name = "改名" + TS
    code, body = api_status("/users/profile", {"username": new_name + "\U0001F3AF"}, token=k["token"], method="PUT")
    check("改名成功", code == 200)
    check("emoji 被剥掉之后才落库",
          ((body.get("data") or {}).get("user") or {}).get("username") == new_name)
    plog = find_log(api("/logs/me", token=k["token"])["data"]["logs"], "user.profile.update") or {}
    pd = plog.get("detail") or {}
    check("改名产生 user.profile.update 日志", bool(plog))
    check("changed 恰好是 ['username']（没改 bio / avatar 就不记）", pd.get("changed") == ["username"])
    check("留下了旧用户名（usernameFrom）", pd.get("usernameFrom") == old_name)
    check("留下了新用户名（usernameTo）", pd.get("usernameTo") == new_name)
    check("摘要里读得到「旧 → 新」",
          old_name in (plog.get("summary") or "") and new_name in (plog.get("summary") or ""))
    check("这一行自己的 username 快照是改名后的新名（其余历史行仍是旧名，快照语义）",
          sql_one(f"SELECT username FROM activity_logs WHERE user_id = {k['uid']} AND action='user.profile.update'") == new_name)
    check("改名前的历史日志仍然是旧名字（快照没被追溯改写）",
          sql_one(f"SELECT username FROM activity_logs WHERE user_id = {k['uid']} AND action='user.register'") == old_name)

    # usernameFrom 是「保存前从库里读出来的旧值」，同样要过 detail 的净化
    api_status("/users/profile", {"username": "新名" + TS}, token=kd["token"], method="PUT")
    kd_from = (find_log(api("/logs/me", token=kd["token"])["data"]["logs"], "user.profile.update") or {})
    kd_from = (kd_from.get("detail") or {}).get("usernameFrom") or ""
    check("脏旧值给到 usernameFrom 时也被净化（detail 一样走 sanitizeDetail）",
          bool(kd_from) and not dirty_chars(kd_from))

    # 只改简介：changed 只记 bio，且不该出现 usernameFrom
    n_before = int(sql_one(f"SELECT COUNT(*) FROM activity_logs WHERE user_id = {k['uid']} AND action='user.profile.update'"))
    api_status("/users/profile", {"bio": "改过的简介" + TS}, token=k["token"], method="PUT")
    n_after = int(sql_one(f"SELECT COUNT(*) FROM activity_logs WHERE user_id = {k['uid']} AND action='user.profile.update'"))
    bio_log = find_log(api("/logs/me", token=k["token"])["data"]["logs"], "user.profile.update") or {}
    bd = bio_log.get("detail") or {}
    check("只改简介也留痕", n_after == n_before + 1)
    check("changed 恰好是 ['bio']", bd.get("changed") == ["bio"])
    check("没改名就不写 usernameFrom（不给下游留无意义的空字段）", "usernameFrom" not in bd)

    # 原样提交：前端表单每次都会把三个字段全量回传，不能因此灌满时间线
    me = api("/users/me", token=k["token"])["data"]
    before_n = int(sql_one(f"SELECT COUNT(*) FROM activity_logs WHERE user_id = {k['uid']}"))
    code, _ = api_status(
        "/users/profile",
        {"username": me["username"], "avatar": me["avatar"], "bio": me["bio"]},
        token=k["token"],
        method="PUT",
    )
    after_n = int(sql_one(f"SELECT COUNT(*) FROM activity_logs WHERE user_id = {k['uid']}"))
    check("原样提交不写日志（否则每次点保存都多一行噪音）", code == 200 and before_n == after_n)

    # 全局兜底：本轮造出的每一行日志，username 列都不能含禁止字符
    ph = ",".join(str(i) for i in ALL_UIDS)
    hex_lines = [
        h
        for h in sql_one(
            f"SELECT HEX(username) FROM activity_logs WHERE user_id IN ({ph}) AND username IS NOT NULL ORDER BY id"
        ).splitlines()
        if h
    ]
    decoded = [bytes.fromhex(h).decode("utf-8", "replace") for h in hex_lines]
    check("本轮全部日志行的 username 列都无禁止字符",
          bool(decoded) and all(not dirty_chars(x) for x in decoded))


def cleanup():
    """清理：activity_logs 不挂外键，**必须显式删**，否则每跑一轮就留一堆垃圾。"""
    for pid in list(PIDS):
        cleanup_project(pid)
    if ALL_UIDS:
        placeholders = ",".join(str(i) for i in ALL_UIDS)
        sql(f"DELETE FROM activity_logs WHERE user_id IN ({placeholders});")
    if UIDS:
        cleanup_users(UIDS)
    # 兜底：动作白名单探针理论上不写库；留存期探针的残留也一并扫掉
    sql("DELETE FROM activity_logs WHERE action = 'evil.inject' OR summary LIKE '%\\_探针';")


if __name__ == "__main__":
    try:
        main()
    finally:
        tracked = ALL_UIDS[:]
        cleanup()
        if tracked:
            ph = ",".join(str(i) for i in tracked)
            print(
                "cleanup: 残留测试用户",
                sql_one(f"SELECT COUNT(*) FROM users WHERE id IN ({ph})"),
                "| 残留日志",
                sql_one(f"SELECT COUNT(*) FROM activity_logs WHERE user_id IN ({ph})"),
            )
    finish()
