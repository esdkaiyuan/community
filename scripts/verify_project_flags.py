#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""验证「编辑推荐」筛选不再是空转入口。

背景：前端首页有「编辑推荐 / 热门」两个筛选 chip，后端把它们翻译成
`is_recommend = 1` / `is_hot = 1`。但全仓没有任何代码写这两个标记位
（线上实测均为 0 条），所以点下去永远是空列表 —— 一个看起来能用、
实际永远为空的假入口。

本脚本钉死三件事：
  1. 标记位有真实的写入路径（backend/scripts/refresh-project-flags.js）
  2. filter=recommend 真的能筛出东西，且筛出的每一项都是被标记的
  3. 页面上点这个 chip 真的有结果，且不再有与排序重复的「热门」chip

分三段：
  N 段 —— 运维脚本真跑（subprocess 起真实 node 进程，干跑 + --apply + --top 精确性）
  A 段 —— API 断言（标记结果 / 筛选口径 / 坏输入不 5xx）
  B 段 —— Playwright 页面断言（点 chip 有结果、无重复 chip、排序仍可用）

运行（仓库根目录）：
  "C:/Users/28916/AppData/Local/Programs/Python/Python313/python.exe" scripts/verify_project_flags.py
"""

import os
import re
import subprocess
import sys
import time
import traceback
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _verify_common import (  # noqa: E402
    FRONT,
    api,
    api_status,
    check,
    cleanup_project,
    create_project,
    finish,
    register,
    sql_one,
)

BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
REFRESH = os.path.join("scripts", "refresh-project-flags.js")
NODE = "node"

TS = time.strftime("%m%d%H%M%S")
PIDS = []
UIDS = []


def run_refresh(extra=()):
    """真跑一次运维脚本，返回 (退出码, 合并输出)"""
    proc = subprocess.run(
        [NODE, REFRESH, *extra],
        cwd=BACKEND,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def flagged_ids():
    rows = sql_one("SELECT GROUP_CONCAT(id) FROM projects WHERE is_recommend = 1 AND deleted_at IS NULL")
    # GROUP_CONCAT 在空集时返回字符串 "NULL"（不是 Python None），直接 int() 会崩
    if not rows or str(rows).strip().upper() == "NULL":
        return set()
    return {int(x) for x in str(rows).split(",") if x.strip().isdigit()}


def score_of(pid):
    """互动分：与运维脚本同一套权重（赞 1 / 评论 2 / 参与 3）"""
    row = sql_one(
        f"SELECT like_count, comment_count, participant_count FROM projects WHERE id = {pid}"
    )
    if not row:
        return -1
    parts = [int(x or 0) for x in str(row).split("\t")]
    return parts[0] * 1 + parts[1] * 2 + parts[2] * 3


# ---------------------------------------------------------------- N 段
def node_section(pid_hot, pid_cold):
    """运维脚本：存在性 + 干跑不写库 + --apply 真写 + --top 精确性"""
    exists = os.path.exists(os.path.join(BACKEND, REFRESH))
    check("N1 运维打标脚本存在（标记位有真实写入路径）", exists)
    if not exists:
        return

    # 干跑：不写库
    before = flagged_ids()
    code, out = run_refresh(["--top=2"])
    check("N2 干跑退出码 0", code == 0)
    check(
        "N3 干跑输出含「将标记」（预览而非静默）",
        "将标记" in out or "已标记" in out,
    )
    check("N4 干跑不写库（标记集合不变）", flagged_ids() == before)

    # --apply：真写
    code, out = run_refresh(["--apply", "--top=2"])
    check("N5 --apply 退出码 0", code == 0)
    after = flagged_ids()
    check("N6 --apply 后标记集合非空", len(after) > 0)
    check(
        "N7 --top=2 精确标记 2 个",
        len(after) == 2,
    )

    # 精确性：高分项目必须在内，低分项目必须不在
    s_hot, s_cold = score_of(pid_hot), score_of(pid_cold)
    check(
        f"N8 高分项目被选中（hot={s_hot} >= cold={s_cold}）",
        s_hot >= s_cold and pid_hot in after,
    )
    if s_hot > s_cold:
        check("N9 低分项目未入选（top 截断生效）", pid_cold not in after)


# ---------------------------------------------------------------- A 段
def api_section(pid_hot, pid_cold):
    """接口：筛选口径 + 坏输入健壮性"""
    res = api("/projects?filter=recommend&pageSize=50")
    data = res.get("data") or {}
    items = data.get("projects") or []
    check("A1 filter=recommend 返回非空（不再是空入口）", len(items) > 0)
    check(
        "A2 返回的每一项 isRecommend 都为真",
        len(items) > 0 and all(i.get("isRecommend") for i in items),
    )
    check(
        "A3 返回总数与库里标记数一致",
        data.get("total") == len(flagged_ids()),
    )

    # 高分项目必然出现在筛选结果里
    ids = {i.get("id") for i in items}
    if score_of(pid_hot) > score_of(pid_cold):
        check("A4 高分项目出现在精选列表", pid_hot in ids)

    # filter=hot 不再依赖永不写入的 is_hot 标记：未知筛选值退化为不筛选
    allres = api("/projects?pageSize=50")
    hotres = api("/projects?filter=hot&pageSize=50")
    check(
        "A5 filter=hot 不再按空标记位筛选（退化为不过滤）",
        (hotres.get("data") or {}).get("total") == (allres.get("data") or {}).get("total"),
    )

    # 坏输入：不得 5xx
    # URL 编码：含空格/控制字符的串会让 http.client 直接抛 InvalidURL，
    # 那是客户端的错而不是接口的错，编码后才是真的在测服务端健壮性
    for bad in ["__proto__", "constructor", "hot; DROP", "1", "%00"]:
        code, _body = api_status(f"/projects?filter={quote(bad, safe='')}")
        check(f"A6 坏 filter={bad!r} 非 5xx", code < 500)
        check(f"A7 坏 filter={bad!r} 响应 code 与状态码一致", (_body or {}).get("code") == code)


# ---------------------------------------------------------------- B 段
def ui_section(token, user, pid_hot):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        errors = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)

        try:
            page.goto(FRONT + "/", wait_until="networkidle")

            chips = page.locator("[data-test='filter-chip']")
            check("B1 筛选 chip 有锚点且至少一个", chips.count() >= 1)

            labels = [chips.nth(i).inner_text().strip() for i in range(chips.count())]
            check("B2 保留「编辑推荐」chip", any("编辑推荐" in t for t in labels))
            check(
                "B3 已移除与排序重复的「热门」chip",
                not any(t.strip() == "热门" for t in labels),
            )

            # 点「编辑推荐」：必须有结果
            rec = page.locator("[data-test='filter-chip'][data-value='recommend']")
            if rec.count():
                rec.first.click()
                page.wait_for_timeout(1500)
                cards = page.locator("[data-test='card-link']")
                check("B4 点「编辑推荐」后列表非空", cards.count() > 0)
                check(
                    "B5 URL 带上 filter=recommend（筛选态可分享）",
                    "filter=recommend" in page.url,
                )
            else:
                check("B4 点「编辑推荐」后列表非空", False)

            # 排序「最热」仍可用（热门语义由排序承担）
            page.goto(FRONT + "/?sort=hot", wait_until="networkidle")
            page.wait_for_timeout(1200)
            cards = page.locator("[data-test='card-link']")
            check("B6 排序「最热」列表非空", cards.count() > 0)

            check("B7 页面无 console 错误", len(errors) == 0)
        finally:
            ctx.close()
            browser.close()


def main():
    owner = register("flagown")
    liker = register("flaglik")
    UIDS.extend([owner["uid"], liker["uid"]])

    # 三个项目：hot 有赞有评论，cold 零互动，mid 一个赞
    pid_hot = create_project(owner["token"], f"热度高{TS}")
    pid_mid = create_project(owner["token"], f"热度中{TS}")
    pid_cold = create_project(owner["token"], f"热度低{TS}")
    PIDS.extend([pid_hot, pid_mid, pid_cold])

    api(f"/projects/{pid_hot}/like", method="POST", token=liker["token"])
    api(f"/projects/{pid_mid}/like", method="POST", token=liker["token"])
    api(f"/projects/{pid_hot}/like", method="POST", token=owner["token"])
    api(
        f"/projects/{pid_hot}/comments",
        {"content": f"热度构造{TS} 这条评论只为拉开互动分差距"},
        token=liker["token"],
    )
    time.sleep(0.8)

    node_section(pid_hot, pid_cold)
    api_section(pid_hot, pid_cold)
    ui_section(owner["token"], owner, pid_hot)


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
            # 打标脚本会把精选标记写到存量项目上；测试项目已删，这里把「本次之前就存在」的
            # 标记保持原样即可（脚本语义就是持续维护，不应由测试回滚）
        except Exception:
            traceback.print_exc()
        if _ERRORED:
            sys.exit(1)
        finish()
