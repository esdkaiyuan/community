# -*- coding: utf-8 -*-
"""scripts/verify_*.py 的共享工具：API / SQL / 断言 / 造数 / 登录注入

在仓库根目录执行即可（运行 `python scripts/verify_x.py` 时脚本目录会进 sys.path，
因此各脚本可以直接 `from _verify_common import ...`）。

    "C:\\Users\\28916\\AppData\\Local\\Programs\\Python\\Python313\\python.exe" scripts/verify_xxx.py

约定（血泪换来的）：
- 断言失败进 assert_fails，console 错误进 console_errors，**两个独立列表**，否则断言失败会被误报成 console error
- 临时账号 / 临时项目一律带时间戳，`finally` 里用 cleanup_project / cleanup_users 清干净
- mysql CLI 必须是 Windows 路径；Python subprocess 用 Git Bash 的 `/c/...` 会 WinError 2
- 数据库凭据与 backend/.env 保持一致（本地开发库）
"""
import json
import subprocess
import sys
import time
import urllib.request

BASE = "http://localhost:5000/api"
FRONT = "http://localhost:3001"
MYSQL = r"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe"  # 必须 Windows 路径
DB_USER = "co_creation_esdk"
DB_PASS = "GchzPPQ8sM6Rc2Xn"
DB_NAME = "co_creation_esdk"
PASSWORD = "test123456"

TS = str(int(time.time()))[-6:]  # 同一轮脚本共用的时间戳后缀，保证临时账号唯一
SETTLE = 0.8  # 通知是 fire-and-forget，写入晚于接口响应

assert_fails = []
console_errors = []


def api(path, data=None, token=None, method=None):
    """调用后端；`/api` 前缀自动补，data 非空默认 POST。"""
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
    """返回单值（-N -B 去表头与对齐）"""
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
    """挂上 console / pageerror 收集器，返回 page 便于链式调用"""
    page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: console_errors.append(str(e)))
    return page


def inject_login(page, token, user):
    """登录态注入：必须先落到同源页面，localStorage 才写得进去"""
    page.goto(f"{FRONT}/login", wait_until="networkidle")
    page.evaluate(
        "([t, u]) => { localStorage.setItem('token', t); localStorage.setItem('userInfo', JSON.stringify(u)) }",
        [token, user],
    )


def register(prefix):
    """注册时间戳临时账号 -> {'token', 'user', 'uid', 'username'}"""
    username = f"{prefix}{TS}"
    data = api(
        "/users/register",
        {"username": username, "email": f"{username}@example.com", "password": PASSWORD},
    )["data"]
    return {"token": data["token"], "user": data["user"], "uid": data["user"]["id"], "username": username}


def create_project(token, title, category_id=1):
    """建临时项目（线上 `category_id` NOT NULL，必须带 categoryId）-> 项目 id"""
    body = {
        "title": title,
        "description": "这是一条用于自动化验证的临时项目描述，验证结束后会被完整清理。",
        "categoryId": category_id,
    }
    return api("/projects", body, token=token)["data"]["id"]


def comment(token, project_id, content, parent_id=None):
    """发评论 / 回复（parent_id 有值即回复）-> comment 对象"""
    body = {"content": content}
    if parent_id:
        body["parentId"] = parent_id
    return api(f"/projects/{project_id}/comments", body, token=token)["data"]["comment"]


def cleanup_project(pid, uids=()):
    """按依赖顺序清干净，避免 MySQL「级联删除超过 30 张表」限制。

    comment_likes 只有 comment_id、没有 project_id，必须走子查询才能按项目清。
    顺序：评论点赞 -> 通知/评论/收藏/点赞/参与 -> 项目 -> 用户。
    先清中间表避免级联链路超限，最后删用户避免被 projects.creator_id 外键挡住。
    """
    sql(f"DELETE FROM comment_likes WHERE comment_id IN (SELECT id FROM project_comments WHERE project_id = {pid});")
    for table in ("notifications", "project_comments", "project_favorites", "project_likes", "project_participants"):
        sql(f"DELETE FROM {table} WHERE project_id = {pid};")
    sql(f"DELETE FROM projects WHERE id = {pid};")
    if uids:
        cleanup_users(uids)


def cleanup_users(uids):
    sql("DELETE FROM users WHERE id IN (%s);" % ",".join(str(i) for i in uids))


def finish():
    """打印汇总；有断言失败或 console 错误则以退出码 1 结束"""
    print("assert failed:", len(assert_fails))
    for f in assert_fails:
        print(" -", f)
    print("console errors:", len(console_errors))
    for e in console_errors[:5]:
        print(" -", e)
    sys.exit(1 if (assert_fails or console_errors) else 0)
