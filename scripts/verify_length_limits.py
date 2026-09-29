# -*- coding: utf-8 -*-
"""输入长度边界与错误文案 · 端到端验证

背景：前端每个输入框都写了 `maxlength`（标题 60 / 介绍 2000 / 简介 200），
但服务端只有**下界**校验（标题 ≥ 4、介绍 ≥ 20），一条上界都没有。于是直接调
API 送超长内容时，请求会一路走到 MySQL 的列宽限制（title VARCHAR(200)、
description/content TEXT），抛 1406「Data too long」，经 errorHandler 兜底
变成用户完全看不懂的 **500「数据存储异常」**。

这是「数据库约束必须在服务层显式校验」那条规则的第二个实例（第一个是
category_id NOT NULL 也变成 500）。前端的 maxlength 只是体验，**直接调 API
也必须得到干净数据** —— 而且必须得到一句人话，而不是 500。

顺带钉住另一类「非业务错误」的文案：body-parser 的 JSON 语法错与请求体超限，
状态码本来是对的（400/413），但 message 是英文技术原文，而前端对 4xx 是
**原样显示**给用户的 —— 用户会看到 "Unexpected token , in JSON at position 19"。

覆盖：
  A. 项目标题边界：60 字通过 / 3 字被拒 / 61 字被拒 / 300 字被拒（均为 400，不是 500）
  B. 项目介绍边界：2000 字通过 / 19 字被拒 / 2001 与 30000 字被拒
  C. 编辑路径同样受约束（PUT 超长被拒，且**原标题/介绍不被改坏**）
  D. 用户资料边界：用户名 20/21、简介 200/201/5000、头像链接 255/256
  E. 非业务错误文案：畸形 JSON → 人话 400；超 1MB 请求体 → 人话 413
  F. 前后端口径一致：UI 的 maxlength 与「服务端接受的最大值」必须相等（防单边漂移）

用法（必须从仓库根目录跑）：python scripts/verify_length_limits.py
"""
import json
import re
import sys
import urllib.error
import urllib.request

from _verify_common import (
    BASE,
    FRONT,
    api,
    api_status,
    attach,
    check,
    cleanup_project,
    cleanup_users,
    console_errors,
    finish,
    inject_login,
    register,
)

# 模块级：注册与造数一旦失败，顶层 finally 也要能兜住（注册限流 429 会在这之前抛）
PIDS = []
UIDS = []

# 通过最小长度校验的合法介绍，作为「只测标题」时的陪衬
DESC_OK = "这是一段用于通过最小长度校验的项目介绍内容，长度足够。"

# 与前端 ProjectForm.vue 的 maxlength 对齐的期望值
UI_TITLE_MAX = 60
UI_DESC_MAX = 2000


def raw_post(path, payload, ctype="application/json"):
    """发原始字节：`api_status()` 会 json.dumps，造不出「畸形 JSON」这个用例"""
    req = urllib.request.Request(BASE + path, data=payload, method="POST")
    req.add_header("Content-Type", ctype)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as err:
        raw = err.read()
        try:
            return err.code, json.loads(raw)
        except ValueError:
            return err.code, {"raw": raw.decode(errors="replace")}


def limit_in(message):
    """从「标题最多 60 个字符」里把 60 抠出来"""
    found = re.search(r"(\d+)", message or "")
    return int(found.group(1)) if found else None


def main():
    print("== A. 项目标题长度边界 ==")
    user = register("len")
    UIDS.append(user["uid"])
    token = user["token"]

    def create(body):
        return api_status("/projects", body, token=token)

    code, res = create({"title": "长" * UI_TITLE_MAX, "description": DESC_OK, "categoryId": 1})
    check(f"标题 {UI_TITLE_MAX} 字（前端上限，刚好用满）创建成功", code == 201)
    pid = res["data"]["id"] if code == 201 else None
    if pid:
        PIDS.append(pid)
        check("读回的标题长度与提交的一致", len(api(f"/projects/{pid}", token=token)["data"]["title"]) == UI_TITLE_MAX)

    check("标题 3 字被拒（下界回归）", create({"title": "三字", "description": DESC_OK, "categoryId": 1})[0] == 400)

    code, res = create({"title": "长" * (UI_TITLE_MAX + 1), "description": DESC_OK, "categoryId": 1})
    check(f"标题 {UI_TITLE_MAX + 1} 字被拒，且是 400 而不是 500", code == 400)
    check("拒绝文案里带上了上限数字", limit_in(res.get("message")) == UI_TITLE_MAX)
    check(f"文案是给用户看的人话（{res.get('message')}）", "最多" in (res.get("message") or ""))

    code, _ = create({"title": "长" * 300, "description": DESC_OK, "categoryId": 1})
    check("标题 300 字同样 400（以前会撞 VARCHAR(200) 变成 500）", code == 400)

    print("\n== B. 项目介绍长度边界 ==")
    code, res = create({"title": "介绍上界探针项目", "description": "介" * UI_DESC_MAX, "categoryId": 1})
    check(f"介绍 {UI_DESC_MAX} 字（前端上限）创建成功", code == 201)
    if code == 201:
        PIDS.append(res["data"]["id"])

    check(
        "介绍 19 字被拒（下界回归）",
        create({"title": "介绍下界探针项目", "description": "介" * 19, "categoryId": 1})[0] == 400,
    )

    code, res = create({"title": "介绍超限探针项目", "description": "介" * (UI_DESC_MAX + 1), "categoryId": 1})
    check(f"介绍 {UI_DESC_MAX + 1} 字被拒，且是 400 而不是 500", code == 400)
    check("拒绝文案里带上了上限数字", limit_in(res.get("message")) == UI_DESC_MAX)

    code, _ = create({"title": "介绍超长探针项目", "description": "介" * 30000, "categoryId": 1})
    check("介绍 30000 字同样 400（以前会撞 TEXT 列 65535 字节变成 500）", code == 400)

    print("\n== C. 编辑路径同样受约束 ==")
    # 上面「刚好用满 60 字」那个项目，拿它验证 PUT 与「被拒后数据没被改坏」
    if pid:
        code, _ = api_status(f"/projects/{pid}", {"title": "长" * (UI_TITLE_MAX + 1)}, token=token, method="PUT")
        check("PUT 超长标题被拒（400）", code == 400)
        check("被拒后原标题未被改动", len(api(f"/projects/{pid}", token=token)["data"]["title"]) == UI_TITLE_MAX)

        code, _ = api_status(f"/projects/{pid}", {"description": "介" * (UI_DESC_MAX + 1)}, token=token, method="PUT")
        check("PUT 超长介绍被拒（400）", code == 400)
        check("被拒后原介绍未被改动", api(f"/projects/{pid}", token=token)["data"]["description"] == DESC_OK)

        # 反向确认编辑功能本身没被这道校验误伤
        code, _ = api_status(f"/projects/{pid}", {"title": "改成合规的新标题"}, token=token, method="PUT")
        check("合规长度的编辑照常成功", code == 200)
    else:
        check("（前置项目创建失败，C 段跳过）", False)

    print("\n== D. 用户资料长度边界 ==")
    check("用户名 20 字通过", api_status("/users/profile", {"username": ("u" * 14) + str(user["uid"]).zfill(6)}, token=token, method="PUT")[0] == 200)
    check("用户名 21 字被拒（下界回归）", api_status("/users/profile", {"username": "u" * 21}, token=token, method="PUT")[0] == 400)

    check("简介 200 字通过", api_status("/users/profile", {"bio": "简" * 200}, token=token, method="PUT")[0] == 200)
    code, res = api_status("/users/profile", {"bio": "简" * 201}, token=token, method="PUT")
    check("简介 201 字被拒，且是 400 而不是 500", code == 400)
    check("简介文案里带上了上限数字", limit_in(res.get("message")) == 200)
    check("简介 5000 字同样 400（以前会撞 TEXT 列变成 500）", api_status("/users/profile", {"bio": "简" * 5000}, token=token, method="PUT")[0] == 400)

    check("头像链接 255 字通过", api_status("/users/profile", {"avatar": "h" * 255}, token=token, method="PUT")[0] == 200)
    code, res = api_status("/users/profile", {"avatar": "h" * 256}, token=token, method="PUT")
    check("头像链接 256 字被拒，且是 400 而不是 500", code == 400)
    check("头像文案里带上了上限数字", limit_in(res.get("message")) == 255)

    print("\n== E. 非业务错误的文案（不能把英文原文甩给用户）==")
    code, res = raw_post("/users/login", b'{"username": "abc",,}')
    check("畸形 JSON 返回 400", code == 400)
    msg = res.get("message") or ""
    check(f"已本地化成中文（{msg}）", "JSON" in msg)
    check("不再回英文解析器原文", ("position" not in msg) and ("Expected" not in msg) and ("Unexpected" not in msg))

    code, res = raw_post("/users/login", json.dumps({"a": "x" * (2 * 1024 * 1024)}).encode())
    check("超过 1MB 的请求体返回 413", code == 413)
    msg = res.get("message") or ""
    check(f"413 也已本地化（{msg}）", "太大" in msg)
    check("不是 body-parser 的英文原文", "entity" not in msg.lower())

    print("\n== F. 前后端口径一致（防单边漂移）==")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = attach(ctx.new_page())
        inject_login(page, token, user["user"])
        page.goto(f"{FRONT}/publish", wait_until="networkidle")
        page.wait_for_timeout(400)

        title_max = int(page.get_attribute("#title", "maxlength"))
        desc_max = int(page.get_attribute("#description", "maxlength"))
        check(f"标题输入框 maxlength = {title_max}，与服务端接受的上限一致", title_max == UI_TITLE_MAX)
        check(f"介绍输入框 maxlength = {desc_max}，与服务端接受的上限一致", desc_max == UI_DESC_MAX)

        ctx.close()
        browser.close()

    console_errors[:] = [e for e in console_errors if not e.startswith("Failed to load resource")]
    check(f"全程零 console 错误（{len(console_errors)} 条）", not console_errors)


if __name__ == "__main__":
    try:
        main()
    finally:
        for pid in PIDS:
            cleanup_project(pid)
        if UIDS:
            cleanup_users(UIDS)
        print(f"已清理临时数据（项目 {len(PIDS)} 个，账号 {len(UIDS)} 个）")
    finish()
