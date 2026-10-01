#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""验证计数列在并发下不丢更新。

背景：全站点赞数 / 评论数 / 参与数过去都是「读出来 +1 再写回」：
    project.like_count += 1; await project.save()
两个并发请求读到同一个旧值、各自写回同一个结果，实际只加了 1 —— 不报错、
不报警，页面上的数字长期被低估。实测 8 个并发点赞只让 like_count +1。

关键：必须用**真并发**的线程来测。顺序打 8 次请求，每次自增都已落库，
必然 +8，看着是绿的其实什么都没测。

四组用例（每组 8 个并发请求，断言 DB 精确 +8 / 精确归零）：
  1. 项目点赞     —— 8 个不同用户同时点赞  -> like_count 精确 +8
  2. 项目取消赞   —— 8 个用户同时取消      -> like_count 精确回到 0（且不为负）
  3. 评论数       —— 8 条并发评论          -> comment_count 精确 +8
  4. 评论点赞     —— 8 个用户同时点赞同一条评论 -> like_count 精确 +8

运行（仓库根目录）：
  "C:/Users/28916/AppData/Local/Programs/Python/Python313/python.exe" scripts/verify_counter_atomicity.py
"""

import os
import sys
import threading
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _verify_common import (  # noqa: E402
    api,
    api_status,
    check,
    cleanup_project,
    create_project,
    finish,
    register,
    sql_one,
)

CONCURRENCY = 8
TS = time.strftime("%m%d%H%M%S")
PIDS = []
UIDS = []


def db_count(sql):
    v = sql_one(sql)
    if v is None or str(v).strip().upper() == "NULL":
        return 0
    return int(v)


def fire_concurrently(callables):
    """真并发：所有线程先就位，再一起发"""
    errors = []
    barrier = threading.Barrier(len(callables))

    def runner(fn):
        try:
            barrier.wait(timeout=10)
            fn()
        except Exception as exc:  # noqa: BLE001
            errors.append(repr(exc))

    threads = [threading.Thread(target=runner, args=(fn,)) for fn in callables]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    return errors


def make_users(n):
    users = []
    for i in range(n):
        u = register(f"cnt{i:02d}")
        UIDS.append(u["uid"])
        users.append(u)
    return users


def section_project_like(pid, users):
    base = db_count(f"SELECT like_count FROM projects WHERE id = {pid}")
    errors = fire_concurrently(
        [lambda u=u: api(f"/projects/{pid}/like", method="POST", token=u["token"]) for u in users]
    )
    time.sleep(1.2)
    got = db_count(f"SELECT like_count FROM projects WHERE id = {pid}")
    check("C1 并发点赞无请求异常", not errors)
    check(
        f"C2 {CONCURRENCY} 个并发点赞使 like_count 精确 +{CONCURRENCY}（实测 +{got - base}）",
        got - base == CONCURRENCY,
    )

    # 取消：同样并发，期望精确归零且不为负
    errors = fire_concurrently(
        [lambda u=u: api(f"/projects/{pid}/like", method="DELETE", token=u["token"]) for u in users]
    )
    time.sleep(1.2)
    got2 = db_count(f"SELECT like_count FROM projects WHERE id = {pid}")
    check("C3 并发取消赞无请求异常", not errors)
    check(
        f"C4 {CONCURRENCY} 个并发取消赞使 like_count 精确回到 {base}（实测 {got2}）",
        got2 == base,
    )
    check("C5 计数不会减成负数", got2 >= 0)


def section_comment_count(pid, users):
    base = db_count(f"SELECT comment_count FROM projects WHERE id = {pid}")
    callables = [
        lambda i=i, u=u: api(
            f"/projects/{pid}/comments",
            {"content": f"并发评论 {i} {TS} 用于验证评论计数不丢更新"},
            token=u["token"],
        )
        for i, u in enumerate(users)
    ]
    errors = fire_concurrently(callables)
    time.sleep(1.5)
    got = db_count(f"SELECT comment_count FROM projects WHERE id = {pid}")
    check("C6 并发评论无请求异常", not errors)
    check(
        f"C7 {CONCURRENCY} 条并发评论使 comment_count 精确 +{CONCURRENCY}（实测 +{got - base}）",
        got - base == CONCURRENCY,
    )


def section_comment_like(pid, users):
    # 取一条刚建的评论
    res = api(f"/projects/{pid}/comments?pageSize=5", token=users[0]["token"])
    rows = (res.get("data") or {}).get("comments") or []
    if not rows:
        check("C8 找到一条评论用于点赞", False)
        return
    cid = rows[0].get("id")
    base = db_count(f"SELECT like_count FROM project_comments WHERE id = {cid}")

    # 评论作者自己点赞会被忽略（业务如此），所以点赞者排除作者
    author_id = rows[0].get("user", {}).get("id")
    likers = [u for u in users if u["uid"] != author_id][:CONCURRENCY]
    if len(likers) < CONCURRENCY:
        # 作者也在列表里，补一个额外账号凑够并发数
        extra = register("cntx")
        UIDS.append(extra["uid"])
        likers = (likers + [extra])[:CONCURRENCY]

    errors = fire_concurrently(
        [lambda u=u: api(f"/projects/{pid}/comments/{cid}/like", method="POST", token=u["token"]) for u in likers]
    )
    time.sleep(1.2)
    got = db_count(f"SELECT like_count FROM project_comments WHERE id = {cid}")
    check("C9 并发评论点赞无请求异常", not errors)
    check(
        f"C10 {CONCURRENCY} 个并发评论点赞精确 +{CONCURRENCY}（实测 +{got - base}）",
        got - base == CONCURRENCY,
    )

    # 响应里的读数不得超过库里的值（防虚报）
    code, body = api_status(f"/projects/{pid}/comments/{cid}/like", method="DELETE", token=likers[0]["token"])
    reported = ((body or {}).get("data") or {}).get("likeCount")
    if isinstance(reported, int):
        check("C11 响应读数不超过库值（不虚报）", reported <= got)


def main():
    owner = register("cntown")
    UIDS.append(owner["uid"])
    pid = create_project(owner["token"], f"并发计数{TS}")
    PIDS.append(pid)

    users = make_users(CONCURRENCY)
    section_project_like(pid, users)
    section_comment_count(pid, users)
    section_comment_like(pid, users)


if __name__ == "__main__":
    _ERRORED = False
    try:
        main()
    except BaseException:
        _ERRORED = True
        traceback.print_exc()
    finally:
        try:
            for pid in PIDS:
                cleanup_project(pid, UIDS)
        except Exception:
            traceback.print_exc()
        if _ERRORED:
            sys.exit(1)
        finish()
