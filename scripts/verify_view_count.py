# -*- coding: utf-8 -*-
"""浏览量（view_count）· 端到端验证

为什么值得单独钉一个脚本：这个字段从前端到后端一直在用（详情页规格条、
README 的功能清单），却**从来没有测试覆盖**。而它踩过一个很严重的实现坑 ——
旧写法是「读出内存里的 view_count，+1 再写回」，两个并发请求会读到同一个旧值、
各自写回同一个结果，**只 +1**。实测 8 个并发请求只让计数 +1（丢 7 次），
也就是说页面上那些「N 次浏览」长期被严重低估，而且不会报任何错。

覆盖四层：
  A. 计数语义：初始为 0 / 首次访问返回的是「自增前」的值 / 列表读取不自增
  B. 并发不丢计数：8 个并发详情请求必须让 DB 精确 +8（这一条钉住上面的修复）
  C. 边界：不存在的项目 404 且不产生计数
  D. 展示层：规格条「浏览次数」与接口一致 / 「N 次浏览」不再与规格条重复 /
     meta 行改显示相对时间 / 跨年项目带年份 / 零 console 错误

用法（必须从仓库根目录跑）：python scripts/verify_view_count.py
"""
import re
import threading
import time

from playwright.sync_api import sync_playwright

from _verify_common import (
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
    sql_one,
)

# 模块级：注册/造数一旦失败，顶层 finally 也要兜得住（注册限流 429 会在这之前抛）
PIDS = []
UIDS = []


def views_of(pid):
    """读 DB 里的真实浏览量（-1 表示读不到）"""
    raw = sql_one(f"SELECT view_count FROM projects WHERE id = {pid};")
    return int(raw) if raw.isdigit() else -1


def wait_views(pid, expect, timeout=8.0):
    """轮询等浏览量落定。

    自增是 fire-and-forget（不阻塞响应），接口返回**不代表**已经写库，
    所以不能紧跟一次即时读就断言——必须轮询到期望值或超时。
    """
    deadline = time.time() + timeout
    value = views_of(pid)
    while value != expect and time.time() < deadline:
        time.sleep(0.2)
        value = views_of(pid)
    return value


def get_detail_concurrently(pid, token, n):
    """并发打 n 个详情请求，返回各自响应里的 viewCount 列表。

    单线程顺序打是**测不出丢更新**的：那样每次自增都已完成，必然 +n。
    必须真并发，才能让多个请求读到同一个旧值。
    """
    results = [None] * n

    def worker(i):
        try:
            results[i] = api(f"/projects/{pid}", token=token)["data"]["viewCount"]
        except Exception as e:  # noqa: BLE001 - 探针：任何异常都记成 None，由断言暴露
            results[i] = f"ERR:{e}"

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results


def main():
    user = register("view")
    UIDS.append(user["uid"])
    token = user["token"]

    pid = api(
        "/projects",
        {
            "title": "浏览量验证项目",
            "description": "这是一条用于自动化验证浏览量计数的临时项目，验证结束后会被完整清理。",
            "categoryId": 1,
        },
        token=token,
    )["data"]["id"]
    PIDS.append(pid)

    print("== A. 计数语义 ==")
    check("新建项目初始浏览量为 0", views_of(pid) == 0)

    detail = api(f"/projects/{pid}", token=token)["data"]
    check(f"详情接口返回 viewCount 字段（{detail['viewCount']}）", "viewCount" in detail)
    # 设计如此：返回的是本次访问**之前**的读数（你看到的是别人看过多少次）
    check("首次访问返回的是自增前的值（0）", detail["viewCount"] == 0)
    check("这次访问把浏览量推到 1", wait_views(pid, 1) == 1)

    # 列表页只展示、不该计数 —— 否则每次刷广场都在给所有项目刷浏览量
    before = views_of(pid)
    api(f"/projects?creatorId={user['uid']}", token=token)
    api(f"/projects?sort=hot", token=token)
    time.sleep(0.6)
    check(f"读列表不自增（{before} -> {views_of(pid)}）", views_of(pid) == before)

    for _ in range(3):
        api(f"/projects/{pid}", token=token)
    check("再连续访问 3 次后为 4", wait_views(pid, 4) == 4)

    print("\n== B. 并发不丢计数（钉住 literal 自增的修复）==")
    N = 8
    base = views_of(pid)
    got = get_detail_concurrently(pid, token, N)
    check(f"并发 {N} 次请求全部成功", all(isinstance(x, int) for x in got))
    final = wait_views(pid, base + N)
    check(f"并发 {N} 次后 DB 精确 +{N}（{base} -> {final}）", final == base + N)
    # 读改写一旦回退成旧实现，这里几乎必挂：实测旧实现 8 并发只 +1
    check(f"没有丢更新（实际增量 {final - base}，期望 {N}）", final - base == N)
    check(
        f"响应里的读数不存在虚报（最大 {max(x for x in got if isinstance(x, int))} <= DB {final}）",
        all(isinstance(x, int) and x <= final for x in got),
    )

    print("\n== C. 边界 ==")
    status, _ = api_status(f"/projects/99999999", token=token)
    check("不存在的项目返回 404", status == 404)
    time.sleep(0.4)
    check("404 不影响本项目的计数", views_of(pid) == final)

    print("\n== D. 展示层 ==")
    db_before_page = views_of(pid)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = attach(ctx.new_page())
        inject_login(page, token, user["user"])
        page.goto(f"{FRONT}/project/{pid}", wait_until="networkidle")
        page.wait_for_timeout(800)

        views_cell = page.locator("[data-test='detail-views']")
        check("规格条有「浏览次数」格", views_cell.count() == 1)
        check(
            f"规格条读数与接口一致（{views_cell.inner_text()!r}）",
            views_cell.locator("p").first.inner_text().strip() == str(db_before_page),
        )

        # 去重防复发：旧版 meta 行还有一个「N 次浏览」，与规格条是同一屏里的同一件事。
        # 「次浏览」不是「浏览次数」的子串，所以这里为 0 才算真去掉了。
        body_text = page.locator("body").inner_text()
        check("「N 次浏览」已不再重复出现", "次浏览" not in body_text)
        check("「浏览次数」全页只出现一次", body_text.count("浏览次数") == 1)

        meta = page.locator("[data-test='detail-meta']").inner_text()
        check(f"meta 行保留「发布于」（{meta!r}）", "发布于" in meta)
        # 同一屏里不再放第二个绝对日期：这里应是相对时间
        check(
            "meta 行用相对时间而不是绝对日期",
            ("刚刚" in meta or "分钟前" in meta or "小时前" in meta or "天前" in meta)
            and "年" not in meta,
        )

        created_cell = page.locator("[data-test='detail-created']")
        check("规格条有「发布日期」格", created_cell.count() == 1)
        check(
            f"当年内的项目只显示月日（{created_cell.locator('p').first.inner_text()!r}）",
            bool(re.fullmatch(r"\d+ 月 \d+ 日", created_cell.locator("p").first.inner_text().strip())),
        )

        page.screenshot(path="docs/screenshots/detail-views-light.png")
        page.emulate_media(color_scheme="dark")
        page.wait_for_timeout(400)
        page.screenshot(path="docs/screenshots/detail-views-dark.png")
        page.emulate_media(color_scheme="light")

        # 跨年项目必须带年份：库里确实躺着 2026-05 的种子数据，只写「5 月 9 日」
        # 会让人以为是今年。改库后重新加载（本次加载的自增不影响这条断言）
        sql_one(f"UPDATE projects SET created_at = '2025-05-09 12:00:00' WHERE id = {pid};")
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(800)
        text = page.locator("[data-test='detail-created']").locator("p").first.inner_text().strip()
        check(f"跨年的项目带年份（{text}）", text.startswith("2025 年"))

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
        print("残留项目:", sum(1 for pid in PIDS if sql_one(f"SELECT COUNT(*) FROM projects WHERE id = {pid};") != "0"))
    finish()
