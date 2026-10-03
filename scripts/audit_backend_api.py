#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""后端接口横向巡检 —— 「坏输入 × 全端点」矩阵。

与 audit_frontend_ui.py（前端横向巡检）互补：
  前端巡检管「页面长得对不对、路由对不对」；
  本脚本管「接口在坏输入下会不会把 500 甩给用户、会不会把英文原文当人话返回」。

五条不变量（本脚本的全部价值所在）：
  I1 任何**用户可控输入**都不得产生 5xx —— 能预见的坏输入必须是 4xx。
  I2 所有响应都是 {code, message, data?}，且 code === HTTP 状态码。
  I3 所有 4xx 的 message 是中文人话，不含英文技术原文。
  I4 受保护端点无 token / 坏 token 一律 401（不是 500，也不是 200）。
  I5 方法不匹配 / 路由不存在一律 404（不是 500）。

为什么值得单独跑一遍：本项目历史上前两轮修掉的「静默 bug」有一半属于 I1
（服务端无上界校验 → 1406 落库失败变 500），说明这类问题成片出现、靠读代码
容易漏。横向矩阵一次覆盖 37 个端点，比逐个功能纵向测更能捞出同类。

用法（仓库根目录）：python scripts/audit_backend_api.py
⚠️ 请求量较大（300+），**请单独跑**，不要与其它验证脚本并跑，否则会撞
   apiLimiter（600 次 / 15 分钟）把结果染红。撞了就重启后端清零再跑。
"""
import sys
import urllib.parse

from _verify_common import (
    TS,
    api_status,
    check,
    cleanup_project,
    cleanup_users,
    create_project,
    register,
    sql_one,
    finish,
)

# 造数登记（只增不减：清理专用，不因断言段摘除而漏清）
UIDS = []
PIDS = []

# 英文技术原文黑名单：4xx 文案里出现任何一个都算「没本地化」。
# 注意**不要**把 "JSON" 放进来 —— 「请求内容不是合法的 JSON」是我们要的本地化结果。
EN_TECH = (
    "must be",
    "Cannot",
    "cannot",
    "Unexpected",
    "position",
    "entity.parse",
    "entity.too",
    "invalid",
    "Invalid",
    "is not",
    "Sequelize",
    "ECONN",
    "ER_",
    "SQL syntax",
    "Unknown column",
    "at line",
    "is required",
    "not a function",
    "reading '",
)

BAD_IDS = (
    "abc",                      # 非数字
    "-1",                       # 负数
    "0",                        # 零
    "99999999999999999999",     # 超出 JS 安全整数（parseInt 后精度丢失）
    "1e20",                     # 科学计数法，parseInt 得到 1
    "1 OR 1=1",                 # 注入串
    "0x10",                     # 十六进制
    "NaN",                      # NaN 字面量
)

BAD_SORTS = (
    "__proto__",                # 原型链：SORT_MAP[sort] 会拿到 Object.prototype
    "constructor",              # 同上，拿到 Function
    "toString",                 # 同上，拿到方法
    "valueOf",
    "hasOwnProperty",
    "prototype",
    "unknown",                  # 普通未知值（这个必须优雅回退）
    "",                         # 空串
    "DROP TABLE projects",      # 注入串
)

BAD_PAGES = (
    "0", "-1", "abc", "1.5", "1e20",
    "99999999999999999999",     # offset 溢出 → 科学计数法进 SQL
    "0x10", "Infinity", "NaN", " ",
)

BAD_SIZES = (
    "0", "-1", "abc",
    "1000",                     # 越过上界（必须被夹到 50）
    "1e20",
    "99999999999999999999",
    "Infinity",
)

# (method, path_template, 是否需登录)
ID_ENDPOINTS = (
    ("GET", "/projects/{id}", False),
    ("GET", "/projects/{id}/participants", False),
    ("GET", "/projects/{id}/related", False),
    ("GET", "/projects/{id}/comments", False),
    ("GET", "/categories/{id}", False),
    ("GET", "/users/{id}", False),
    ("PUT", "/projects/{id}", True),
    ("DELETE", "/projects/{id}", True),
    ("POST", "/projects/{id}/like", True),
    ("DELETE", "/projects/{id}/like", True),
    ("POST", "/projects/{id}/participate", True),
    ("DELETE", "/projects/{id}/participate", True),
    ("POST", "/projects/{id}/favorite", True),
    ("DELETE", "/projects/{id}/favorite", True),
    ("POST", "/projects/{id}/comments", True),
    ("DELETE", "/projects/{id}/comments/1", True),
    ("POST", "/projects/{id}/comments/1/like", True),
    ("DELETE", "/projects/{id}/comments/1/like", True),
)

# auth 端点 + 不存在的受保护路径
AUTH_GET = (
    "/users/me",
    "/users/me/comments",
    "/users/me/stats",
    "/users/me/favorites",
    "/users/profile",
    "/notifications",
    "/notifications/unread-count",
    "/logs/me",
)

WRITE_ENDPOINTS = (
    ("POST", "/users/register", None),
    ("POST", "/users/login", None),
    ("POST", "/projects", True),
    ("PUT", "/projects/{pid}", True),
    ("PUT", "/users/profile", True),
    ("PUT", "/users/password", True),
    ("POST", "/projects/{pid}/comments", True),
)


def q(value):
    return urllib.parse.quote(str(value), safe="")


# ---------------------------------------------------------------- 三个通用断言

def no_5xx(label, status):
    check("%s → %s，不是 5xx" % (label, status), status < 500)


def shape_ok(label, status, body):
    good = (
        isinstance(body, dict)
        and body.get("code") == status
        and isinstance(body.get("message"), str)
        and bool(body["message"].strip())
    )
    check("%s 响应形状 {code,message} 且 code==%s" % (label, status), good)


def chinese_msg(label, status, body):
    """只在 4xx 上检查本地化：5xx 的前端会换成「服务暂时不可用」，不算泄露。"""
    if not (400 <= status < 500):
        return
    msg = body.get("message", "") if isinstance(body, dict) else ""
    hit = [w for w in EN_TECH if w in msg]
    check(
        "%s 的 4xx 文案是中文人话%s" % (label, "（混入英文 %s）" % hit if hit else ""),
        not hit,
    )


def audit(label, path, data=None, token=None, method=None):
    """发一次请求，跑「不 5xx + 形状 + 文案」三件套，返回 (status, body)"""
    status, body = api_status(path, data, token=token, method=method)
    no_5xx(label, status)
    shape_ok(label, status, body)
    chinese_msg(label, status, body)
    return status, body


# ---------------------------------------------------------------------- 各段

def sec_a_control(pid, uid, token):
    """对照组：合法输入必须照常成功。

    没有这一段，一个「把所有请求都 400 掉」的假修复也能让上面全绿。
    """
    print("== A. 对照：合法输入照常成功（防「一律 400」式假修复）==")
    for label, path in (
        ("GET /health", "/health"),
        ("GET /categories", "/categories"),
        ("GET /projects", "/projects"),
        ("GET /projects?sort=latest", "/projects?sort=latest"),
        ("GET /projects?sort=hot", "/projects?sort=hot"),
        ("GET /projects?sort=participants", "/projects?sort=participants"),
        ("GET /projects?page=2&pageSize=5", "/projects?page=2&pageSize=5"),
        ("GET /projects?pageSize=1000（夹到上界）", "/projects?pageSize=1000"),
        ("GET /projects/tags", "/projects/tags"),
        ("GET /projects/%d" % pid, "/projects/%d" % pid),
        ("GET /projects/%d/participants" % pid, "/projects/%d/participants" % pid),
        ("GET /projects/%d/related" % pid, "/projects/%d/related" % pid),
        ("GET /projects/%d/comments" % pid, "/projects/%d/comments" % pid),
        ("GET /categories/1", "/categories/1"),
        ("GET /users/%d" % uid, "/users/%d" % uid),
        ("GET /users/me（带 token）", "/users/me"),
        ("GET /projects（带 token）", "/projects"),
    ):
        tk = token if "带 token" in label else None
        status, body = audit(label, path, token=tk)
        if "带 token" not in label:
            check("%s 返回 200" % label, status == 200)


def sec_b_sort():
    print("== B. 排序参数：原型链枚举名 / 注入串都必须优雅回退 ==")
    for s in BAD_SORTS:
        label = "GET /projects?sort=%s" % (s if s else "(空)")
        status, _ = audit(label, "/projects?sort=" + q(s))
        check("%s 回退到默认排序而不是报错（200）" % label, status == 200)

    # 合法值不能被误伤
    for s in ("latest", "hot", "participants", "recommend", "trending"):
        status, _ = audit("GET /projects?sort=%s（合法）" % s, "/projects?sort=" + s)
        check("合法 sort=%s 仍返回 200" % s, status == 200)


def sec_c_pagination():
    print("== C. 分页参数：page / pageSize 无上界会让 offset 溢出成科学计数法 ==")
    for p in BAD_PAGES:
        label = "GET /projects?page=%s" % (p if p.strip() else "(空格)")
        status, _ = audit(label, "/projects?page=" + q(p))
        check("%s 不 500 且不报错（200）" % label, status == 200)

    for s in BAD_SIZES:
        label = "GET /projects?pageSize=%s" % s
        status, _ = audit(label, "/projects?pageSize=" + q(s))
        check("%s 不 500 且不报错（200）" % label, status == 200)

    # 分页参数在其它列表接口上一样要安全
    for path, label in (
        ("/projects?page=1e20", "GET /projects"),
        ("/projects/tags?limit=1e20", "GET /projects/tags"),
    ):
        status, _ = audit("%s（page/limit 溢出）" % label, path)
        check("%s 不 500" % label, status < 500)


def sec_c2_protected_pagination(token, pid):
    """受保护列表端点：分页收口（utils/pagination）的直接受益者。

    这一段是「同一个根因在多处复发」的证明 —— 修复前 `page` 溢出只在
    /projects 上被测到，但 6 个 service 是同一份复制粘贴的代码，全都有。
    """
    print("== C2. 受保护列表端点：分页参数同样不能 500 ==")
    for path, label in (
        ("/notifications?page=1e20", "GET /notifications"),
        ("/notifications?page=99999999999999999999&pageSize=1000", "GET /notifications"),
        ("/users/me/comments?page=1e20", "GET /users/me/comments"),
        ("/users/me/favorites?page=1e20&pageSize=99999", "GET /users/me/favorites"),
        ("/logs/me?page=1e20", "GET /logs/me"),
        ("/logs/me?projectId=abc&page=1e20", "GET /logs/me（非法 projectId）"),
        ("/logs/me?action=project.create&page=1e20", "GET /logs/me（合法筛选 + 溢出）"),
        ("/projects/%d/participants?page=1e20" % pid, "GET /projects/:id/participants"),
        ("/projects?page=1e20&pageSize=1e20", "GET /projects"),
        ("/projects?categoryId=abc&creatorId=abc&participantId=abc", "GET /projects（筛选值格式错）"),
    ):
        status, _ = audit(label, path, token=token)
        check("%s 分页溢出时仍是 200" % label, status == 200)

    # action 是**固定枚举**，传非枚举值明确拒绝而不是静默忽略 —— 这是有意行为，
    # 单独钉住：静默忽略会让用户以为「筛选生效了，只是没数据」。
    status, body = audit("GET /logs/me?action=…（非法枚举）", "/logs/me?action=" + q("../"), token=token)
    check("非法 action 是 400 而不是 5xx", status == 400)
    check("非法 action 的文案说明了「不支持」", "支持" in (body.get("message") or ""))


def sec_d_path_params(token):
    print("== D. 路径参数：非数字 / 负数 / 溢出 / 注入串一律 4xx ==")
    for method, tpl, need_auth in ID_ENDPOINTS:
        tk = token if need_auth else None
        for bad in BAD_IDS:
            path = tpl.format(id=q(bad))
            label = "%s %s（id=%s）" % (method, tpl.replace("{id}", "…"), bad)
            audit(label, path, token=tk, method=method)

    # 双层路径参数：评论 id 也要扛得住
    for bad in ("abc", "1e20", "-1"):
        audit(
            "DELETE /projects/{id}/comments/…（cid=%s）" % bad,
            "/projects/1/comments/" + q(bad),
            token=token,
            method="DELETE",
        )


def sec_e_auth():
    print("== E. 鉴权：无 token / 坏 token 一律 401 ==")
    bad_tokens = (None, "", "abc", "a.b.c", "x" * 500)
    for path in AUTH_GET:
        for tk in bad_tokens:
            label = "GET %s（token=%s）" % (path, "无" if tk is None else ("空" if tk == "" else tk[:6] + "…"))
            status, _ = audit(label, path, token=tk)
            check("%s 是 401 而不是 5xx / 200" % label, status == 401)

    # 写端点同样
    for method, path, _ in (
        ("POST", "/projects", {"title": "x"}),
        ("PUT", "/users/profile", {"bio": "x"}),
        ("PUT", "/users/password", {"oldPassword": "x", "newPassword": "y"}),
        ("POST", "/projects/1/like", None),
    ):
        status, _ = audit("%s %s（无 token）" % (method, path), path, data=_, method=method)
        check("%s %s 无 token 时是 401" % (method, path), status == 401)


def sec_f_body_shape(pid, token):
    print("== F. 请求体形状：数组 / 字符串 / 数字 / 类型错都不能 500 ==")
    weird_bodies = (
        ("空对象", {}),
        ("数组", []),
        ("字符串", "just a string"),
        ("数字", 123),
        ("嵌套数组", [[1, 2], [3]]),
    )
    for method, tpl, need_auth in WRITE_ENDPOINTS:
        path = tpl.format(pid=pid)
        tk = token if need_auth else None
        for name, body in weird_bodies:
            label = "%s %s（body=%s）" % (method, path, name)
            status, _ = audit(label, path, data=body, token=tk, method=method)
            # 非对象 body 必须被拒：能落库就是脏数据
            if method == "POST" and tpl == "/projects":
                check("%s 不会创建成功（不是 201）" % label, status != 201)
                check("%s 是 4xx 而不是 5xx" % label, 400 <= status < 500)

    # 类型错字段：数字当标题、数组当分类、对象当标签
    for name, body in (
        ("title 是数字", {"title": 12345, "description": "验证用描述内容占位", "categoryId": 1}),
        ("title 是数组", {"title": ["a", "b"], "description": "验证用描述内容占位", "categoryId": 1}),
        ("categoryId 是数组", {"title": "类型错验证标题", "description": "验证用描述内容占位", "categoryId": [1, 2]}),
        ("categoryId 是对象", {"title": "类型错验证标题", "description": "验证用描述内容占位", "categoryId": {"x": 1}}),
        ("tags 是字符串", {"title": "类型错验证标题", "description": "验证用描述内容占位", "categoryId": 1, "tags": "not-array"}),
        ("tags 里混对象", {"title": "类型错验证标题", "description": "验证用描述内容占位", "categoryId": 1, "tags": [{"$ne": 1}]}),
        ("content 是对象", {"content": {"x": 1}}),
    ):
        if "content" in str(body):
            audit("POST comments（%s）" % name, "/projects/%d/comments" % pid, data=body, token=token)
        else:
            audit("POST /projects（%s）" % name, "/projects", data=body, token=token)

    # query 参数被污染成数组 / 对象（Express 默认解析 ?x[]=1 / ?x[a]=b）
    print("== F2. query 污染：?x[]=1 / ?x[a]=b 会让 req.query.x 变成数组或对象 ==")
    for label, path in (
        ("数组形态", "/projects?categoryId[]=1&categoryId[]=2"),
        ("对象形态", "/projects?categoryId[ne]=1"),
        ("嵌套对象", "/projects?creatorId[$gt]=0"),
        ("tag 数组", "/projects?tag[]=a&tag[]=b"),
        ("sort 对象", "/projects?sort[a]=b"),
        ("page 数组", "/projects?page[]=1&page[]=2"),
    ):
        status, _ = audit("GET /projects %s" % label, path)
        check("query %s 不 500" % label, status < 500)


def sec_g_method_and_route(token):
    print("== G. 方法不匹配 / 路由不存在一律 404（不是 500）==")
    # 注意：`/logs` 与 `/projects` 都挂了 auth，鉴权跑在路由匹配**之前** ——
    # 不带 token 会先拿到 401，根本走不到「方法不匹配」那一步（实测踩过）。
    # 所以这两条必须带 token，测的才是路由行为而不是鉴权。
    for label, method, path, tk in (
        ("POST /health", "POST", "/health", None),
        ("PUT /categories", "PUT", "/categories", None),
        ("DELETE /projects/tags（带 token）", "DELETE", "/projects/tags", token),
        ("POST /logs/me（带 token）", "POST", "/logs/me", token),
        ("PATCH /projects", "PATCH", "/projects", None),
        ("GET /不存在的路径", "GET", "/no-such-endpoint", None),
        ("GET /projects/1/不存在的子路径", "GET", "/projects/1/no-such-sub", None),
    ):
        status, _ = audit(label, path, token=tk, method=method)
        check("%s 是 404" % label, status == 404)


def sec_h_not_found(token):
    print("== H. 资源不存在必须是 404（而且文案是中文）==")
    big = sql_one("SELECT COALESCE(MAX(id), 0) + 100000 FROM projects")
    for label, path, tk, method in (
        ("GET 不存在的项目", "/projects/" + big, None, "GET"),
        ("GET 不存在的分类", "/categories/" + big, None, "GET"),
        ("GET 不存在的用户", "/users/" + big, None, "GET"),
        ("GET 不存在项目的评论", "/projects/%s/comments" % big, None, "GET"),
        ("DELETE 不存在的项目", "/projects/" + big, token, "DELETE"),
        ("PUT 不存在的项目", "/projects/" + big, token, "PUT"),
        ("POST 不存在项目的点赞", "/projects/%s/like" % big, token, "POST"),
        ("GET 不存在项目的定位", "/projects/%s/comments/locate?commentId=1" % big, None, "GET"),
    ):
        status, _ = audit(label, path, token=tk, method=method)
        check("%s 是 404" % label, status == 404)


def sec_i_msg_quality():
    print("== I. 错误文案专项：这几条是用户天天会碰到的 ==")
    cases = (
        ("畸形 JSON", "POST", "/users/login", None),
        ("缺字段注册", "POST", "/users/register", {"username": "only_name"}),
        ("缺字段登录", "POST", "/users/login", {"email": "x@example.com"}),
    )
    for label, method, path, data in cases:
        status, body = audit(label, path, data=data, method=method)
        check("%s 是 4xx" % label, 400 <= status < 500)
        msg = body.get("message", "") if isinstance(body, dict) else ""
        check("%s 文案非空且是中文" % label, bool(msg) and any("\u4e00" <= c <= "\u9fff" for c in msg))


def main():
    pid = int(sql_one("SELECT id FROM projects WHERE deleted_at IS NULL ORDER BY id LIMIT 1"))
    uid = int(sql_one("SELECT id FROM users ORDER BY id LIMIT 1"))
    print("对照用真实数据：project=%d user=%d" % (pid, uid))

    me = register("auditapi")
    UIDS.append(me["uid"])
    token = me["token"]

    # 写路径的坏 body 必须打在**自己的**项目上：拿别人的项目会在权限校验那步
    # 先被 403 拦住，请求体校验根本走不到（会误判成「已覆盖」）。
    my_pid = create_project(token, "auditprobe%s 巡检用临时项目" % TS)
    PIDS.append(my_pid)

    sec_a_control(pid, uid, token)
    sec_b_sort()
    sec_c_pagination()
    sec_c2_protected_pagination(token, pid)
    sec_d_path_params(token)
    sec_e_auth()
    sec_f_body_shape(my_pid, token)
    sec_g_method_and_route(token)
    sec_h_not_found(token)
    sec_i_msg_quality()


if __name__ == "__main__":
    try:
        main()
    finally:
        for p in PIDS:
            cleanup_project(p)
        tracked = UIDS[:]
        if tracked:
            # 临时账号是这些探测项目的 creator，删用户会级联带走它们
            cleanup_users(tracked)
            ph = ",".join(str(i) for i in tracked)
            print(
                "cleanup: 残留用户",
                sql_one("SELECT COUNT(*) FROM users WHERE id IN (%s)" % ph),
                "| 残留项目",
                sql_one("SELECT COUNT(*) FROM projects WHERE creator_id IN (%s)" % ph),
                "| 残留日志",
                sql_one("SELECT COUNT(*) FROM activity_logs WHERE user_id IN (%s)" % ph),
            )
        finish()
