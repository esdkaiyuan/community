# -*- coding: utf-8 -*-
"""第 19 轮：评论富文本（**粗体** / `行内代码` / ``` 围栏代码块）。

N 段：richText.js 零 import 纯函数 —— 复制成 .mjs 交 node 跑真实现断言。
A 段：API/存储 —— 内容原样入库（净化链不吃语法，HEX 字节级比对）、mention 回归、
      mention 通知落库。
B 段：Playwright 渲染 —— 粗体/行内代码/围栏/降级/代码区不解析/@ 在粗体内。
"""
import re
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _verify_common import (  # noqa: E402
    FRONT,
    api,
    attach,
    check,
    cleanup_project,
    create_project,
    finish,
    inject_login,
    register,
    sql_one,
)
from playwright.sync_api import sync_playwright  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RICH_SRC = ROOT / "frontend" / "src" / "utils" / "richText.js"
PIDS = []
UIDS = []
TS = time.strftime("%m%d%H%M%S")

# ---------------- N 段：node 跑真实现 ----------------

NODE_TEST = r"""
import { parseFences, parseInline } from "./richText_copy.mjs";
const t = (name, cond) => { if (!cond) throw new Error("NFAIL " + name) };

// 围栏：闭合 / 语言标注 / 多行
let b = parseFences("前文\n```js\nconst a = 1\nconst b = 2\n```\n后文");
t("fence closed blocks", b.length === 3);
t("fence text head", b[0].type === "text" && b[0].text === "前文");
t("fence body exact", b[1].type === "fence" && b[1].text === "const a = 1\nconst b = 2");
t("fence tail", b[2].text === "后文");

// 围栏：未闭合 -> 整段纯文本降级（内容零丢失）
b = parseFences("孤立围栏行\n**abc");
t("fence unclosed degrade count", b.length === 1 && b[0].type === "text");
t("fence unclosed keep", b[0].text === "孤立围栏行\n**abc");

// 围栏：空输入
t("fence empty", parseFences("").length === 1 && parseFences("")[0].text === "");

// 行内：代码 / 粗体 / 混排
let s = parseInline("a `x y` b **加粗** c");
t("inline len", s.length === 5);
t("inline code", s[1].type === "code" && s[1].text === "x y");
t("inline bold", s[3].type === "bold" && s[3].text === "加粗");

// 代码优先：行内代码里的粗体语法不解析
s = parseInline("`**不是粗体**`");
t("code first", s.length === 1 && s[0].type === "code" && s[0].text === "**不是粗体**");

// 降级：未闭合粗体 / 单反引号 / 粗体内含 *
s = parseInline("未闭合 **粗体");
t("bold unclosed", s.length === 1 && s[0].type === "text" && s[0].text.includes("**粗体"));
s = parseInline("`半截代码");
t("code unclosed", s.length === 1 && s[0].text.includes("`半截代码"));
s = parseInline("**a*b**");
t("bold with star literal", s.length === 1 && s[0].type === "text");

// 粗体跨行不识别
s = parseInline("**a\nb**");
t("bold no newline", s.length === 1 && s[0].type === "text");

console.log("NODE_ALL_OK");
"""


def node_section():
    if not RICH_SRC.exists():
        check("N0 richText.js 存在", False)
        return
    src = RICH_SRC.read_text(encoding="utf-8")
    check("N1 richText.js 零 import（node 可直测前提）",
          re.search(r"^\s*import\s", src, re.M) is None)
    tmp = RICH_SRC.parent / "richText_copy.mjs"
    test_file = RICH_SRC.parent / "_rich_node_test.mjs"
    try:
        shutil.copyfile(RICH_SRC, tmp)
        test_file.write_text(NODE_TEST, encoding="utf-8")
        r = subprocess.run(
            ["node", test_file.name], cwd=str(RICH_SRC.parent),
            capture_output=True, encoding="utf-8", errors="replace", timeout=60,
        )
        ok = r.returncode == 0 and "NODE_ALL_OK" in r.stdout
        check("N2 node 断言全过（围栏/行内/降级/代码优先）", ok)
        if not ok:
            print("  [N 诊断]", (r.stdout + r.stderr)[-400:])
    finally:
        for f in (tmp, test_file):
            try:
                f.unlink()
            except OSError:
                pass
            except BaseException as err:
                # 🔥 本机沙箱的删除守卫抛的是 SystemExit（继承 BaseException，
                # **不是** OSError），所以上面的 `except OSError` 抓不住它 ——
                # 结果清理动作把整个脚本带崩，退出码 1，几十条已通过的断言全被
                # 记成「这个脚本失败」。删除失败不影响本轮结论，吞掉即可。
                # （实测：守卫触发时 stderr 会打 [safe-delete][SAFE_DELETE_BULK_CONFIRM_REQUIRED]）
                print(f"  [清理跳过] {f.name}: 沙箱删除守卫拦下（{type(err).__name__}），不影响结论")


# ---------------- A 段：API / 存储 ----------------

def row_val(row):
    if row is None:
        return None
    if isinstance(row, (tuple, list)):
        return row[0]
    return row


def main():
    node_section()

    owner = register("richown")
    UIDS.append(owner["uid"])
    name2 = register("richal")
    UIDS.append(name2["uid"])
    pid = create_project(owner["token"], f"富文本验证{TS}")
    PIDS.append(pid)

    rich_content = (
        f"RICH19A **加粗文本** 与 `行内代码` 以及:\n"
        f"```js\nconst a = 1\nconst b = 2\n```\n"
        f"@{owner['username']} 请查收"
    )
    deg_content = "RICH19B 未闭合 **粗体 与 `半截代码\n``` 孤立围栏行"
    code_content = "RICH19C `**不是粗体**`"
    bold_mention = f"RICH19D **@{name2['username']} 加粗提及**"

    # rich_content 由 name2 发表：内容里 @ 的是 owner，不能自己提自己（会被正确排除）
    r1 = api(f"/projects/{pid}/comments", {"content": rich_content}, token=name2["token"])
    r2 = api(f"/projects/{pid}/comments", {"content": deg_content}, token=owner["token"])
    r3 = api(f"/projects/{pid}/comments", {"content": code_content}, token=owner["token"])
    r4 = api(f"/projects/{pid}/comments", {"content": bold_mention}, token=owner["token"])
    cid = {k: ((r.get("data") or {}).get("comment") or {}).get("id")
           for k, r in (("A", r1), ("B", r2), ("C", r3), ("D", r4))}

    # HEX 比较：mysql CLI batch 模式会把内容里的真实换行转义成字面反斜杠n，
    # 直接比文本会让多行内容假红（HEX 输出无转义，字节级铁证）
    for key, want in (("A", rich_content), ("B", deg_content), ("C", code_content), ("D", bold_mention)):
        got = row_val(sql_one(
            f"SELECT HEX(content) FROM project_comments WHERE id = {cid[key]}"
        ))
        check(f"A 存储-{key} 原样入库（未清洗语法）",
              isinstance(got, str) and got.lower() == want.encode("utf-8").hex())

    # mention 回归（第 18 轮口径不受影响）
    m1 = [m.get("username") for m in ((r1.get("data") or {}).get("mentions") or [])]
    m4 = [m.get("username") for m in ((r4.get("data") or {}).get("mentions") or [])]
    check("A mention-回归 owner", owner["username"] in m1)
    check("A mention-粗体内也识别", name2["username"] in m4)

    # mention 通知落库（轮询：notify 是 fire-and-forget）
    deadline = time.time() + 6
    n_rows = -1
    while time.time() < deadline:
        n_rows = int(row_val(sql_one(
            f"SELECT COUNT(*) FROM notifications WHERE type='mention' "
            f"AND user_id={name2['uid']} AND comment_id={cid['D']}"
        )) or 0)
        if n_rows >= 1:
            break
        time.sleep(0.5)
    check("A mention 通知落库（粗体内提及）", n_rows >= 1)

    # ---------------- B 段：渲染 ----------------
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(viewport={"width": 1440, "height": 900}).new_page()
        console_errors = []
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        attach(page)
        inject_login(page, owner["token"], owner)
        page.goto(f"{FRONT}/project/{pid}", wait_until="networkidle")
        page.wait_for_selector("[data-test='comment-item']", timeout=10000)

        def item(marker):
            loc = page.locator("[data-test='comment-item']").filter(has_text=marker)
            loc.wait_for(timeout=5000)
            return loc.first

        def txt_of(container, sel):
            # 红证阶段元素不存在：快速返回 None 让断言 FAIL，绝不 30s 超时抛异常
            loc = container.locator(sel)
            return loc.inner_text(timeout=2000) if loc.count() else None

        it_a = item("RICH19A")
        check("B1 围栏代码块渲染 + 多行精确保留",
              txt_of(it_a, "[data-test='rich-pre']") == "const a = 1\nconst b = 2")
        check("B2 行内代码渲染", txt_of(it_a, "[data-test='rich-code']") == "行内代码")
        check("B3 粗体渲染", txt_of(it_a, "[data-test='rich-bold']") == "加粗文本")
        check("B4 @ 高亮共存", txt_of(it_a, "[data-test='mention']") == f"@{owner['username']}")

        it_b = item("RICH19B")
        check("B5 未闭合定界符零元素降级",
              it_b.locator("[data-test='rich-pre']").count() == 0
              and it_b.locator("[data-test='rich-bold']").count() == 0
              and it_b.locator("[data-test='rich-code']").count() == 0)
        txt_b = it_b.inner_text()
        check("B6 降级内容零丢失（原文都在）",
              "``` 孤立围栏行" in txt_b and "**粗体" in txt_b and "`半截代码" in txt_b)

        it_c = item("RICH19C")
        check("B7 代码区优先（粗体语法按字面进 code）",
              txt_of(it_c, "[data-test='rich-code']") == "**不是粗体**"
              and it_c.locator("[data-test='rich-bold']").count() == 0)

        it_d = item("RICH19D")
        check("B8 粗体内 @ 高亮",
              it_d.locator("[data-test='rich-bold']").count() == 1
              and txt_of(it_d, "[data-test='rich-bold'] [data-test='mention']")
              == f"@{name2['username']}")

        check("B9 零 console 错误", len(console_errors) == 0)
        if console_errors:
            print("  [B 诊断 console]", console_errors[:3])
        browser.close()


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
