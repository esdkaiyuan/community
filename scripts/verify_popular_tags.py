#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""验证热门标签：SQL 聚合与内存聚合等价，且实现真的改成了 SQL 聚合。

背景：listPopularTags 原本把**全表** projects 的 tags 捞进 Node，再用 Map 逐条
聚合 —— 全表扫描 + 大内存 + 无上限，数据量一大就拖垮列表页。改成单条 SQL
（JSON_TABLE + GROUP BY）后，数据库只返回聚合结果。

这类「纯重构」的验证重点是**行为等价**，所以：
  A 段 —— 用造出来的标签数据，把接口结果与「Python 侧独立聚合的真值」逐项对照
          （真值从库里自己读、自己算，不复用实现里的任何代码）
  B 段 —— limit 边界与坏输入
  C 段 —— 源码层断言：实现确实是 SQL 聚合，不再是「捞全表进内存」

见证红：改之前 C 段应当红（实现还是内存聚合），A/B 段照绿 —— 这正说明
「实现换了、行为没变」，而不是「没测到」。

运行（仓库根目录）：
  "C:/Users/28916/AppData/Local/Programs/Python/Python313/python.exe" scripts/verify_popular_tags.py
"""

import json
import os
import re
import sys
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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVICE = os.path.join(ROOT, "backend", "src", "services", "project.service.js")

TS = time.strftime("%m%d%H%M%S")
PIDS = []
UIDS = []

# 三个标签，计数刻意错开（3 / 2 / 1），避免并列时的排序口径差异干扰对照
PLAN = [("开源", 3), ("硬件", 2), ("AI", 1)]


def ground_truth():
    """独立于实现，直接从库里读标签并自己聚合"""
    raw = sql_one(
        "SELECT GROUP_CONCAT(IFNULL(tags, '') SEPARATOR ';;') "
        "FROM projects WHERE deleted_at IS NULL"
    )
    counter = {}
    if raw and str(raw).strip().upper() != "NULL":
        for chunk in str(raw).split(";;"):
            chunk = chunk.strip()
            if not chunk:
                continue
            try:
                names = json.loads(chunk)
            except Exception:  # noqa: BLE001
                continue
            if not isinstance(names, list):
                continue
            for n in names:
                name = str(n or "").strip()
                if name:
                    counter[name] = counter.get(name, 0) + 1
    return counter


def top_n(counter, n):
    return sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[:n]


def section_api():
    truth = ground_truth()
    res = api("/projects/tags")
    got = res.get("data") or []
    expect = top_n(truth, 12)

    check("A1 接口返回列表", isinstance(got, list))
    check(
        f"A2 与库里独立聚合的真值一致（接口 {len(got)} 项 / 真值 {len(expect)} 项）",
        len(got) == len(expect),
    )
    check(
        "A3 每项的名称与计数都一致",
        all(
            i < len(expect) and g.get("name") == expect[i][0] and g.get("count") == expect[i][1]
            for i, g in enumerate(got)
        ),
    )
    check(
        "A4 按项目数倒序",
        all(got[i].get("count", 0) >= got[i + 1].get("count", 0) for i in range(len(got) - 1)),
    )

    # 造的标签必须出现在结果里且计数正确
    by_name = {g.get("name"): g.get("count") for g in got}
    for name, want in PLAN:
        check(
            f"A5 标签「{name}」计数正确（期望 {want} 实得 {by_name.get(name)}）",
            by_name.get(name) == want,
        )


def section_limits():
    r = api("/projects/tags?limit=2")
    got = r.get("data") or []
    check("B1 limit=2 生效", len(got) == 2)

    for bad in ["abc", "0", "-1", "99999999999999999999", "__proto__"]:
        code, body = api_status(f"/projects/tags?limit={bad}")
        check(f"B2 坏 limit={bad!r} 非 5xx", code < 500)
        check(f"B3 坏 limit={bad!r} 响应 code 与状态码一致", (body or {}).get("code") == code)


def section_source():
    src = open(SERVICE, encoding="utf-8").read()
    m = re.search(r"exports\.listPopularTags\s*=\s*async.*?\n\}", src, re.S)
    body = m.group(0) if m else ""
    check("C1 找得到 listPopularTags 实现", bool(body))
    check(
        "C2 实现走 SQL 聚合（含 JSON_TABLE + GROUP BY）",
        "JSON_TABLE" in body and "GROUP BY" in body.upper(),
    )
    check(
        "C3 不再把全表捞进内存做 Map 聚合",
        "counter.set" not in body and "counter.get" not in body,
    )


def main():
    owner = register("tagown")
    UIDS.append(owner["uid"])

    # 按计划造标签：每个标签造 N 个项目（标题带时间戳，便于清理核对）
    for name, count in PLAN:
        for i in range(count):
            pid = create_project(
                owner["token"], f"标签{name}{i}{TS}", tags=[name]
            )
            PIDS.append(pid)
    time.sleep(0.5)

    section_api()
    section_limits()
    section_source()


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
