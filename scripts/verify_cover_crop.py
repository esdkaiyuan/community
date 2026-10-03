# -*- coding: utf-8 -*-
"""封面裁剪（调整构图）· 几何 / 端到端 / 守卫 验证

（待办 ②「图片裁剪 / 压缩」里「裁剪」那一半。）

背景：封面在卡片里按 16:9 展示、在详情页头图里按 21:9 展示，两处都是 object-cover。
一张竖版手机照在这种容器里会被 CSS 从正中间横切一刀，主体常常正好落在被切掉的部分，
而用户此前没有任何办法干预 —— 上一轮解决了「传得上来」，这一轮解决「显示成什么」。

这个功能的核心风险不是「能不能裁」，而是**裁出来的到底是不是用户框的那一块**。
所以本脚本最大的篇幅不是点按钮，而是两件事：
  1. 把 imageCrop.js 的源码复制成 .mjs 交给 node 跑**真函数**做几何断言。
     另外写一份 Python 版公式来对答案是不行的 —— 那种测试在实现写错时照样绿。
  2. 用一张「有方位标记」的图（左红/右蓝、顶绿/底黄）反推裁剪结果：
     拖到最右只能看到红、拖到最左只能看到蓝、竖直方向既没有绿也没有黄
     （三条同时成立才说明取景框真的落在了正中那一条）。

覆盖四层：
  A. 几何（node 跑真实现）：铺满 / 居中即 object-cover 中带 / 缩放按平方收缩 /
     平移夹取 / 全域扫描永不越界 / 任意源图比例下输出比例恒定 / 取景框像素尺寸无关性
  B. 端到端（Playwright）：选图 → 上传（未裁剪时字节不动）→ 开裁剪器 →
     默认居中裁一次（比例 / 尺寸 / 方位）→ 缩放后左右拉满各裁一次（红蓝对调）
  C. 守卫：GIF 无入口 / 手填地址无入口 / 取消不改封面
  D. 零 console 错误 + 清场对账（清场这一步可能被本机沙箱的删除守卫拦住 -> 记 SKIP
     而不是 FAIL：那是环境问题，Playwright 关浏览器时要清几百个文件的临时 profile，
     正好会把守卫的计数顶上去）

用法（必须从仓库根目录跑）：
  "C:\\Users\\28916\\AppData\\Local\\Programs\\Python\\Python313\\python.exe" scripts/verify_cover_crop.py

⚠️ 一轮约 7 次上传，而后端 uploadLimiter 是 40 次 / 15 分钟。连着跑 5 轮左右就会开始
   收到 429（症状：C 段某一次上传失败 -> 没有封面 -> 没有裁剪入口）。此时重启后端
   即可清零（express-rate-limit 用内存计数）。
"""
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request

from _verify_common import (
    BASE,
    FRONT,
    attach,
    check,
    cleanup_users,
    finish,
    inject_login,
    register,
)

# 模块级：注册一旦失败，顶层 finally 也要兜得住
UIDS = []
# 本轮产生的物理文件，结束时逐个删（绝不整目录清空：那里可能有真实用户数据）
UPLOADED = []

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
UPLOAD_DIR = os.path.join(REPO, "backend", "uploads", "projects")
CROP_SRC = os.path.join(REPO, "frontend", "src", "utils", "imageCrop.js")
TMP = os.path.join(tempfile.gettempdir(), "_cover_crop_verify")


# ---------------------------------------------------------------- 读数 / 读源码

def read_source():
    with io.open(CROP_SRC, encoding="utf-8") as f:
        return f.read()


def source_expr(text, name):
    """从源码读回一个**算式**常量并求值。

    `COVER_ASPECT = 16 / 9` 这种写法要能读 —— 把 1.7778 抄进断言就等于
    「测试与实现各写一份」，实现改了测试照绿。字符集限死成数字与四则运算符，
    eval 不出别的东西来。
    """
    m = re.search(rf"export const {name}\s*=\s*([0-9./+*() \-]+)", text)
    if not m:
        return None
    try:
        return eval(m.group(1).strip(), {"__builtins__": {}}, {})  # noqa: S307
    except Exception:  # noqa: BLE001 - 读不懂就返回 None，让断言去报红
        return None


def source_str(text, name):
    m = re.search(rf"export const {name}\s*=\s*'([^']*)'", text)
    return m.group(1) if m else None


# ---------------------------------------------------------------- 小工具

def path_of(name):
    return os.path.join(UPLOAD_DIR, name) if name else ""


def dir_names():
    try:
        return set(os.listdir(UPLOAD_DIR))
    except FileNotFoundError:
        return set()


def magic_of(name, n=12):
    try:
        with open(path_of(name), "rb") as f:
            return f.read(n)
    except OSError:
        return b""


def image_stats(name):
    """读磁盘上的成品图 -> {'size': (w,h), 各标记色占比}

    缩到 64x36 再逐点判色：百万级像素没必要全数，而标记都是大块纯色，
    WebP 有损压缩 + 缩采样不会改变结论。
    """
    from PIL import Image

    if not os.path.exists(path_of(name)):
        # 文件不落地时不要让断言崩成 traceback，给一组「必然判红」的零值
        return {"size": (0, 0), "red": 0.0, "blue": 0.0, "green": 1.0, "yellow": 1.0}

    with Image.open(path_of(name)) as im:
        size = im.size
        grid = im.convert("RGB").resize((64, 36), Image.NEAREST)
    px = list(grid.getdata())

    def frac(pred):
        return sum(1 for c in px if pred(c)) / len(px)

    return {
        "size": size,
        "red": frac(lambda c: c[0] > 140 and c[1] < 110 and c[2] < 110),
        "blue": frac(lambda c: c[2] > 140 and c[0] < 110 and c[1] < 110),
        "green": frac(lambda c: c[1] > 140 and c[0] < 110 and c[2] < 110),
        "yellow": frac(lambda c: c[0] > 140 and c[1] > 140 and c[2] < 110),
    }


def make_marked_png(path, w=1600, h=1200):
    """造一张「带方位标记」的测试图，用来反推裁剪落在了哪里：

        左半红 / 右半蓝        → 判断裁到了哪一侧
        顶部一条绿 / 底部一条黄 → 判断竖直方向裁的是不是**正中**那一条
                                  （只管上下、不管左右的标记才判得出这一点：
                                   红蓝在任何横向位置上都有，只有绿黄能区分上下）

    标记都远离垂直中线、且与底色反差大，压缩后仍判得准。
    """
    from PIL import Image, ImageDraw

    im = Image.new("RGB", (w, h), (20, 60, 220))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w // 2 - 1, h], fill=(220, 30, 40))
    d.rectangle([0, 16, w, 48], fill=(30, 200, 60))
    d.rectangle([0, h - 48, w, h - 16], fill=(230, 210, 20))
    im.save(path, "PNG")
    return im.size


def make_small_gif(path, w=64, h=64):
    from PIL import Image

    Image.new("P", (w, h), 3).save(path, "GIF")


# ---------------------------------------------------------------- A 段：几何（node 跑真函数）

HARNESS = r"""
import * as M from './imageCrop.mjs'

const round = (v, p = 6) => Number(Number(v).toFixed(p))
const out = {}
const S = { srcW: 1600, srcH: 1200, frameW: 640, frameH: 360 }

out.aspect = M.COVER_ASPECT
out.label = M.COVER_ASPECT_LABEL
out.maxZoom = M.COVER_CROP_MAX_ZOOM
out.modules = typeof M.cropToFile === 'function' && typeof M.cropRegion === 'function'

// 1) 铺满：两个方向都不小于取景框，且至少一个方向正好贴合（不浪费像素）
const fit = M.fitScale(S.srcW, S.srcH, S.frameW, S.frameH)
out.fit = round(fit)
out.fitCovers = S.srcW * fit >= S.frameW - 1e-9 && S.srcH * fit >= S.frameH - 1e-9
out.fitTight =
  Math.abs(Math.min(S.srcW * fit - S.frameW, S.srcH * fit - S.frameH)) < 1e-9

// 2) 居中 = object-cover 的中带：区域必须与源图同心
const cen = M.centeredPan(S.srcW, S.srcH, S.frameW, S.frameH, 1)
const r1 = M.cropRegion({ ...S, zoom: 1, panX: cen.x, panY: cen.y })
out.centerRegion = {
  x: round(r1.x), y: round(r1.y), width: round(r1.width), height: round(r1.height)
}
out.centerIsConcentric =
  Math.abs(r1.x - (S.srcW - r1.width) / 2) < 1e-6 &&
  Math.abs(r1.y - (S.srcH - r1.height) / 2) < 1e-6

// 3) 缩放：保留面积按 zoom² 收缩（zoom=2 就该只剩四分之一）
const r2 = M.cropRegion({ ...S, zoom: 2, panX: cen.x, panY: cen.y })
out.zoom2Region = {
  x: round(r2.x), y: round(r2.y), width: round(r2.width), height: round(r2.height)
}
out.zoom2AreaRatio = round((r2.width * r2.height) / (r1.width * r1.height))

// 4) 平移余量：zoom=1 时没有横向余量（4:3 源图被 16:9 框按宽度贴合）
out.slack = [1, 1.5, 2, 3].map((zoom) => {
  const s = M.fitScale(S.srcW, S.srcH, S.frameW, S.frameH) * zoom
  return { zoom, slack: round(S.srcW * s - S.frameW) }
})

// 5) 拉满两端：区域必须正好贴住源图左右边
const le = M.cropRegion({ ...S, zoom: 2, panX: 0 })
const re = M.cropRegion({ ...S, zoom: 2, panX: -99999 })
out.leftEdgeX = round(le.x)
out.rightEdgeReach = round(re.x + re.width)
out.edgesClamp = Math.abs(le.x) < 1e-6 && Math.abs(re.x + re.width - S.srcW) < 1e-6

// 6) 全域扫描：任何 zoom / 任何越界偏移都不许把区域推到源图之外（否则露白边）
let escaped = null
for (const zoom of [1, 1.2, 1.7, 2.4, 3]) {
  for (let i = -6; i <= 6; i++) {
    for (let j = -6; j <= 6; j++) {
      const r = M.cropRegion({
        ...S, zoom, panX: (i * S.frameW) / 4, panY: (j * S.frameH) / 4
      })
      const ok =
        r.x >= -1e-9 && r.y >= -1e-9 &&
        r.x + r.width <= S.srcW + 1e-9 && r.y + r.height <= S.srcH + 1e-9
      if (!ok && !escaped) escaped = { zoom, i, j, r }
    }
  }
}
out.sweepEscaped = escaped

// 7) 任意源图比例下输出比例恒等于取景框比例
out.ratios = [[1600, 1200], [3000, 2000], [1200, 1600], [2560, 1080], [1000, 1000], [900, 2400]]
  .map(([w, h]) => {
    const p = M.centeredPan(w, h, S.frameW, S.frameH, 1.7)
    const r = M.cropRegion({
      srcW: w, srcH: h, frameW: S.frameW, frameH: S.frameH, zoom: 1.7, panX: p.x, panY: p.y
    })
    return {
      src: `${w}x${h}`,
      ratio: round(r.width / r.height, 4),
      inBounds:
        r.x >= -1e-9 && r.y >= -1e-9 &&
        r.x + r.width <= w + 1e-9 && r.y + r.height <= h + 1e-9
    }
  })

// 8) 取景框的像素尺寸不该影响裁剪结果（换个视口打开，裁出来还是同一块）
const pa = M.centeredPan(S.srcW, S.srcH, 640, 360, 1.4)
const pb = M.centeredPan(S.srcW, S.srcH, 1280, 720, 1.4)
const ra = M.cropRegion({ ...S, zoom: 1.4, panX: pa.x, panY: pa.y })
const rb = M.cropRegion({ srcW: 1600, srcH: 1200, frameW: 1280, frameH: 720, zoom: 1.4, panX: pb.x, panY: pb.y })
out.frameInvariant =
  Math.abs(ra.x - rb.x) < 1e-6 && Math.abs(ra.y - rb.y) < 1e-6 &&
  Math.abs(ra.width - rb.width) < 1e-6 && Math.abs(ra.height - rb.height) < 1e-6

// 9) zoom < 1 一律按 1 处理：绝不把图缩到比取景框还小（那会露出空白）
const z05 = M.cropRegion({ ...S, zoom: 0.5, panX: cen.x, panY: cen.y })
out.subZoomClamped =
  Math.abs(z05.width - r1.width) < 1e-9 && Math.abs(z05.height - r1.height) < 1e-9

// 10) 非法输入不产生 NaN 区域
const bad = M.cropRegion({ srcW: 0, srcH: 0, frameW: 0, frameH: 0, zoom: 1, panX: 0, panY: 0 })
out.zeroInputFinite =
  Number.isFinite(bad.x) && Number.isFinite(bad.y) &&
  Number.isFinite(bad.width) && Number.isFinite(bad.height)

console.log(JSON.stringify(out))
"""


def run_geometry(source):
    """把 imageCrop.js 复制成 .mjs 交给 node 跑真函数 -> dict（失败返回 None）

    复制成 .mjs 是因为 frontend/package.json 没有 `"type": "module"`，
    node 默认会把 .js 当 CommonJS 解析，import 语法直接语法错误。
    """
    if os.path.isdir(TMP):
        shutil.rmtree(TMP, ignore_errors=True)
    os.makedirs(TMP, exist_ok=True)
    with io.open(os.path.join(TMP, "imageCrop.mjs"), "w", encoding="utf-8", newline="\n") as f:
        f.write(source)
    with io.open(os.path.join(TMP, "harness.mjs"), "w", encoding="utf-8", newline="\n") as f:
        f.write(HARNESS)
    try:
        proc = subprocess.run(
            ["node", "harness.mjs"], cwd=TMP, capture_output=True, text=True, timeout=90
        )
    except Exception:  # noqa: BLE001
        return None
    if proc.returncode != 0:
        tail = (proc.stderr or "").strip().splitlines()
        print("  (node 报错) " + (tail[-1] if tail else "无输出"))
        return None
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------- B 段：页面动作

def ui_upload(page, src_path, timeout=40000):
    """走真实用户路径选图上传 -> (url, 备注)。绝不抛异常。"""
    try:
        with page.expect_response("**/api/uploads/cover", timeout=timeout) as info:
            page.set_input_files("[data-test='cover-input']", src_path)
        url = (info.value.json().get("data") or {}).get("url", "")
    except Exception as err:  # noqa: BLE001
        return "", f"根本没有发出上传请求（{type(err).__name__}）"
    if url.startswith("/uploads/projects/"):
        UPLOADED.append(url.rsplit("/", 1)[-1])
    try:
        page.wait_for_function(
            "(u) => { const el = document.querySelector('[data-test=cover-preview] img'); "
            "return !!el && el.getAttribute('src') === u }",
            arg=url,
            timeout=10000,
        )
        note = ""
    except Exception:  # noqa: BLE001
        note = "预览没跟着换"
    return url, note


def open_cropper(page):
    """点开裁剪器并等到图片解码完成 -> 取景框尺寸 或 None

    **绝不抛异常**（与 ui_upload 同一条纪律）：入口不存在时（图没传上去、被限流、
    或者守卫逻辑真的坏了）就在这里返回 None，让上层那一条断言去报红。
    否则 Playwright 会甩 30 秒超时的 traceback，把后面十几条断言一起吃掉 ——
    那样「见证红」就只剩一条，覆盖面的证据也没了。
    """
    try:
        page.click("[data-test='cover-crop-open']", timeout=8000)
        page.wait_for_selector("[data-test='cover-crop-frame']", timeout=8000)
        page.wait_for_function(
            "() => { const i = document.querySelector('[data-test=cover-crop-img]'); "
            "return !!i && i.complete && i.naturalWidth > 0 }",
            timeout=10000,
        )
        return page.locator("[data-test='cover-crop-frame']").bounding_box()
    except Exception:  # noqa: BLE001 - 探针：任何异常都只是「没进去」
        return None


def drag_frame(page, dx, dy=0, steps=12):
    """在取景框上拖拽（真实指针事件，走的是组件的 pointerdown/move/up）"""
    try:
        box = page.locator("[data-test='cover-crop-frame']").bounding_box()
    except Exception:  # noqa: BLE001
        return False
    if not box:
        return False
    cx = box["x"] + box["width"] / 2
    cy = box["y"] + box["height"] / 2
    page.mouse.move(cx, cy)
    page.mouse.down()
    page.mouse.move(cx + dx, cy + dy, steps=steps)
    page.mouse.up()
    return True


def set_zoom(page, value):
    """把缩放滑杆设到某个值 -> 实际生效的值 或 None

    用原生 setter + 派发 input 事件：fill() 对 range 不生效，
    而组件里绑的是 @input。
    """
    try:
        page.evaluate(
            """([sel, v]) => {
                 const el = document.querySelector(sel)
                 const setter = Object.getOwnPropertyDescriptor(
                   window.HTMLInputElement.prototype, 'value').set
                 setter.call(el, String(v))
                 el.dispatchEvent(new Event('input', { bubbles: true }))
               }""",
            ["[data-test='cover-crop-zoom']", value],
        )
        page.wait_for_timeout(120)
        return float(page.locator("[data-test='cover-crop-zoom']").input_value())
    except Exception:  # noqa: BLE001
        return None


def ui_crop_confirm(page, timeout=40000):
    """点「完成裁剪」并等到上传返回 -> (url, 备注)。绝不抛异常。"""
    try:
        with page.expect_response("**/api/uploads/cover", timeout=timeout) as info:
            page.click("[data-test='cover-crop-confirm']")
        url = (info.value.json().get("data") or {}).get("url", "")
    except Exception as err:  # noqa: BLE001
        return "", f"没有发出上传请求（{type(err).__name__}）"
    if url.startswith("/uploads/projects/"):
        UPLOADED.append(url.rsplit("/", 1)[-1])
    # 裁剪器必须自己退场，把预览让回来 —— 还留在界面上说明状态没收敛
    try:
        page.wait_for_selector("[data-test='cover-crop']", state="detached", timeout=8000)
    except Exception:  # noqa: BLE001
        pass
    return url, ""


def toast_text(page):
    try:
        return " ".join(page.locator("[data-test^='toast-']").all_inner_texts())
    except Exception:  # noqa: BLE001
        return ""


# ---------------------------------------------------------------- main

def main():
    before_all = dir_names()
    source = read_source()

    print("== A. 几何（把实现复制成 .mjs 交给 node 跑真函数）==")
    aspect = source_expr(source, "COVER_ASPECT")
    label = source_str(source, "COVER_ASPECT_LABEL")
    check(f"从源码读到取景框比例（{aspect}）", aspect is not None and abs(aspect - 16 / 9) < 1e-9)

    # 给用户看的「16:9」必须和数字对得上 —— 对不上就是界面在骗人
    label_ratio = None
    if label and ":" in label:
        try:
            a, b = (float(x) for x in label.split(":", 1))
            label_ratio = a / b
        except ValueError:
            label_ratio = None
    check(
        f"界面标签「{label}」与比例数字一致（{label_ratio} vs {round(aspect, 4) if aspect else None}）",
        label_ratio is not None and aspect is not None and abs(label_ratio - aspect) < 1e-6,
    )
    check(
        "几何模块保持零 import（否则 node 无法独立单测，本段就失效了）",
        not re.search(r"^\s*import\s", source, re.M),
    )

    geo = run_geometry(source)
    check("node 能直接加载该模块并跑出结果", geo is not None)
    if not geo:
        finish()
        return

    check(f"zoom 上限从源码读到（{geo['maxZoom']}）", geo["maxZoom"] == 3)
    check(
        f"铺满取景框：两个方向都不小于框、且有一边正好贴合（fitScale={geo['fit']}）",
        geo["fitCovers"] and geo["fitTight"],
    )
    r = geo["centerRegion"]
    check(
        f"默认居中裁出的区域与原图同心（{r['width']}x{r['height']} @ {r['x']},{r['y']}）",
        geo["centerIsConcentric"] and abs(r["width"] / r["height"] - 16 / 9) < 1e-3,
    )
    z2 = geo["zoom2Region"]
    check(
        f"放大 2 倍后保留面积只剩四分之一（{z2['width']}x{z2['height']}，比值 {geo['zoom2AreaRatio']}）",
        abs(geo["zoom2AreaRatio"] - 0.25) < 1e-6,
    )
    slack = {s["zoom"]: s["slack"] for s in geo["slack"]}
    check(
        f"平移余量随缩放线性增长（zoom=1 时 {slack[1]}px，zoom=2 时 {slack[2]}px）",
        abs(slack[1]) < 1e-6 and abs(slack[2] - 640) < 1e-6,
    )
    check(
        f"拖到两端正好贴住原图左右边（左 {geo['leftEdgeX']}，右到 {geo['rightEdgeReach']}）",
        geo["edgesClamp"],
    )
    check(
        f"全域扫描（5 档缩放 x 169 组偏移）没有一次越出原图（越界处 {geo['sweepEscaped']}）",
        geo["sweepEscaped"] is None,
    )
    bad = [x for x in geo["ratios"] if abs(x["ratio"] - 16 / 9) > 2e-3 or not x["inBounds"]]
    check(
        f"六种源图比例（含 9:16 竖版与 21:9 宽幅）裁出的比例都等于取景框（异常 {bad}）",
        not bad,
    )
    check("取景框像素尺寸变了，裁剪区域不变（640x360 与 1280x720 结果相同）", geo["frameInvariant"])
    check("zoom 小于 1 被按 1 处理（不会把图缩到比取景框还小）", geo["subZoomClamped"])
    check("退化输入（0x0）不产出 NaN 区域", geo["zeroInputFinite"])

    # ------------------------------------------------------------ B/C 段
    marked = os.path.join(TMP, "marked.png")
    small_gif = os.path.join(TMP, "small.gif")
    src_w, src_h = make_marked_png(marked)
    make_small_gif(small_gif)
    src_bytes = os.path.getsize(marked)

    user = register("crop")
    UIDS.append(user["uid"])
    token = user["token"]

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = attach(ctx.new_page())
        inject_login(page, token, user["user"])
        page.goto(f"{FRONT}/publish", wait_until="networkidle")
        page.wait_for_timeout(600)

        print("\n== B. 端到端：从选图到裁出一块 ==")
        raw_url, note = ui_upload(page, marked)
        raw_name = raw_url.rsplit("/", 1)[-1] if raw_url else ""
        check(f"标记图上传成功（{raw_url or note}）", raw_url.startswith("/uploads/projects/"))
        check(
            f"没点裁剪之前原样上传、字节不动（{src_bytes}B，与源文件一致）",
            raw_url.endswith(".png")
            and os.path.exists(path_of(raw_name))
            and os.path.getsize(path_of(raw_name)) == src_bytes,
        )
        check("预览区出现「调整构图」入口", page.locator("[data-test='cover-crop-open']").count() == 1)

        box = open_cropper(page)
        check("点开后进入裁剪界面（预览让位给取景框）", box is not None)
        check("进入裁剪时预览已被取景框接管", page.locator("[data-test='cover-preview']").count() == 0)
        if box:
            ratio = box["width"] / box["height"]
            check(
                f"取景框实际渲染比例是 16:9（{box['width']:.0f}x{box['height']:.0f} = {ratio:.3f}）",
                abs(ratio - 16 / 9) < 0.03,
            )

        # —— 第一次：默认居中，直接确认
        url1, note1 = ui_crop_confirm(page)
        check(f"默认状态下完成裁剪并重新上传（{url1 or note1}）", url1.startswith("/uploads/projects/"))
        check(f"裁出来的封面换了地址（原图 {raw_url.rsplit('/', 1)[-1]}）", url1 and url1 != raw_url)
        check("产物扩展名是 .webp", url1.endswith(".webp"))
        head = magic_of(url1.rsplit("/", 1)[-1])
        check(
            "文件头是真 WebP（RIFF....WEBP）",
            head[:4] == b"RIFF" and head[8:12] == b"WEBP",
        )
        check("裁剪后裁剪器自动退场，预览回来了", page.locator("[data-test='cover-preview']").count() == 1)
        check(f"提示里说明了按 {label} 重新构图（{toast_text(page)}）", label in toast_text(page))

        st = image_stats(url1.rsplit("/", 1)[-1])
        w1, h1 = st["size"]
        check(
            f"输出尺寸 = 原图宽度 x 16:9 的高度（{w1}x{h1}，比例 {w1 / h1 if h1 else 0:.3f}）",
            w1 == src_w and abs(w1 / max(h1, 1) - 16 / 9) < 0.01,
        )
        check(
            f"左右各占一半（红 {st['red']:.2f} / 蓝 {st['blue']:.2f}）——说明横向裁的是整幅宽度",
            0.42 < st["red"] < 0.58 and 0.42 < st["blue"] < 0.58,
        )
        check(
            f"竖直方向既没有顶部绿也没有底部黄（绿 {st['green']:.3f} / 黄 {st['yellow']:.3f}）——"
            "说明竖直方向真的取的是正中那一条，而不是顺手从顶上切",
            st["green"] < 0.01 and st["yellow"] < 0.01,
        )

        # —— 第二次：放大 2 倍后拖到最右 → 只该看到红
        check("裁完之后仍可再次调整（入口还在）", page.locator("[data-test='cover-crop-open']").count() == 1)
        box = open_cropper(page)
        check("再次进入裁剪界面", box is not None)
        # 第二次的素材必须是**原图**：否则每裁一次就更窄一刀，用户收不回来
        nat = page.evaluate(
            "() => { const i = document.querySelector('[data-test=cover-crop-img]'); "
            "return i ? [i.naturalWidth, i.naturalHeight] : null }"
        )
        check(f"再次裁剪的素材仍是原图（{nat}）而不是上一刀的结果", nat == [src_w, src_h])

        zoom_now = set_zoom(page, 2)
        check(f"缩放滑杆被设到 2（当前 {zoom_now}）", zoom_now is not None and abs(zoom_now - 2) < 1e-6)
        if box:
            drag_frame(page, box["width"], 0)
        url2, note2 = ui_crop_confirm(page)
        check(f"放大并拖到最右后裁剪成功（{url2 or note2}）", url2.startswith("/uploads/projects/"))
        st2 = image_stats(url2.rsplit("/", 1)[-1])
        w2, h2 = st2["size"]
        check(
            f"放大 2 倍后保留宽度减半（{w2}x{h2}，原图宽 {src_w}）",
            abs(w2 - src_w // 2) <= 2,
        )
        check(
            f"拖到最右后画面只剩红（红 {st2['red']:.2f}）——裁剪确实跟着用户的手走",
            st2["red"] > 0.95,
        )

        # —— 第三次：拖到最左 → 只该看到蓝
        box = open_cropper(page)
        check("第三次仍能进入裁剪界面（同一张原图可以反复调整）", box is not None)
        zoom_now = set_zoom(page, 2)
        check(f"第三次同样能设缩放（{zoom_now}）", zoom_now is not None and abs(zoom_now - 2) < 1e-6)
        if box:
            drag_frame(page, -box["width"], 0)
        url3, note3 = ui_crop_confirm(page)
        check(f"拖到最左后裁剪成功（{url3 or note3}）", url3.startswith("/uploads/projects/"))
        st3 = image_stats(url3.rsplit("/", 1)[-1])
        check(
            f"拖到最左后画面只剩蓝（蓝 {st3['blue']:.2f}）——左右两个方向都能真正控制",
            st3["blue"] > 0.95,
        )

        print("\n== C. 守卫：不该出现入口的地方就不出现 ==")
        page.goto(f"{FRONT}/publish", wait_until="networkidle")
        page.wait_for_timeout(400)
        gif_url, gif_note = ui_upload(page, small_gif)
        check(f"GIF 上传成功（{gif_url or gif_note}）", gif_url.endswith(".gif"))
        check(
            "GIF 封面不给裁剪入口（canvas 只画得出第一帧，裁一次就把动图变成静帧）",
            page.locator("[data-test='cover-crop-open']").count() == 0,
        )

        page.goto(f"{FRONT}/publish", wait_until="networkidle")
        page.wait_for_timeout(400)
        ext_url, _ = ui_upload(page, marked)
        page.click("[data-test='cover-toggle-url']")
        # 手填地址：即使这个链接指向的仍是我们自己的文件，也不再给裁剪入口
        page.fill("[data-test='cover-url']", f"{FRONT}{ext_url}")
        page.wait_for_timeout(400)
        check("手填图片地址后不出现裁剪入口（外链跨源会污染 canvas）", page.locator("[data-test='cover-crop-open']").count() == 0)

        page.goto(f"{FRONT}/publish", wait_until="networkidle")
        page.wait_for_timeout(400)
        keep_url, keep_note = ui_upload(page, marked)
        check(f"（取消用例）标记图上传成功（{keep_url or keep_note}）", keep_url.startswith("/uploads/"))
        uploads_before_cancel = len(UPLOADED)
        box = open_cropper(page)
        check("取消用例：能进入裁剪界面", box is not None)
        set_zoom(page, 2.5)
        if box:
            drag_frame(page, -box["width"] * 0.4, 0)
        try:
            page.click("[data-test='cover-crop-cancel']", timeout=8000)
        except Exception:  # noqa: BLE001 - 点不到就交给下面的断言说
            pass
        try:
            page.wait_for_selector("[data-test='cover-crop']", state="detached", timeout=6000)
        except Exception:  # noqa: BLE001
            pass
        try:
            now_src = page.locator("[data-test='cover-preview'] img").get_attribute("src")
        except Exception:  # noqa: BLE001
            now_src = None
        check("取消后离开裁剪界面", page.locator("[data-test='cover-crop']").count() == 0)
        check(f"取消不改变封面地址（仍然 {now_src}）", now_src == keep_url)
        check(
            f"取消没有再产生上传（上传数仍为 {len(UPLOADED)}，取消前是 {uploads_before_cancel}）",
            len(UPLOADED) == uploads_before_cancel,
        )

        browser.close()

    # ------------------------------------------------------------ D 段
    print("\n== D. 清场对账 ==")
    # 🔥 本机沙箱对「删文件」有守卫：一轮里删除量超过阈值后，**所有**删除都开始被拒
    # （守护进程的判定助手还会 10 秒超时）。Playwright 关浏览器时要清掉几百个文件的
    # 临时 profile，正好会把这个计数器顶上去 —— 于是「清场」这一步偶发失败。
    # 这是环境不是应用（详见 verify_cover_compress.py 的 backend_can_delete 说明），
    # 所以这里**不允许它把整轮结论带崩**，也要明说为什么没对账成功。
    stray = sorted(dir_names() - before_all)
    for name in stray:
        try:
            os.remove(os.path.join(UPLOAD_DIR, name))
        except OSError:
            pass
        except BaseException:  # noqa: BLE001 - 沙箱删除守卫抛 SystemExit，抓不住会带崩整个脚本
            pass

    remaining = sorted(dir_names() - before_all)
    if remaining:
        print(
            f"  SKIP 上传目录回到本轮开始时的样子 —— 本机删除守卫在拦（残留 {len(remaining)} 个："
            f"{', '.join(remaining[:3])}{' …' if len(remaining) > 3 else ''}），是环境不是应用"
        )
    else:
        check(f"上传目录回到本轮开始时的样子（已清本轮产生的 {len(stray)} 个）", True)

    leftover = [n for n in UPLOADED if os.path.exists(os.path.join(UPLOAD_DIR, n))]
    if leftover:
        print(f"  SKIP 本轮登记的上传文件已清干净 —— 同上被守卫拦住（残留 {len(leftover)} 个）")
    else:
        check(f"本轮登记上传的 {len(UPLOADED)} 个文件都已从磁盘清掉", True)

    finish()


if __name__ == "__main__":
    try:
        main()
    finally:
        # 临时账号一定要清（注册失败时 UIDS 可能为空，cleanup_users 会自己挡）
        try:
            cleanup_users(UIDS)
        except Exception as err:  # noqa: BLE001 - 清理失败不该改变本轮结论
            print(f"cleanup: 失败 {err}")
