# -*- coding: utf-8 -*-
"""封面图片上传 · 端到端验证

背景：本仓库历史上确实做过图片上传（库里残留着项目 14-17，标题含
「图片上传测试_20260509」「大文件上传测试_20260509」，cover_image 指向
/uploads/projects/*.png），但上传能力在后来的重构中整体丢失 ——
后端既没有 multer 也没有静态服务，所有封面请求全是 404。
本脚本防的就是这个功能再次悄无声息地消失。

覆盖七层：
  A. 鉴权与成功路径：未登录 401 / 上传 200 / 返回相对路径 / 服务端重命名 / 静态可访问
  B. 校验边界：非图片 MIME、伪造魔数（文本改名 .png）、超过 5MB、字段名错
     —— 并且**被拒后磁盘上不留垃圾文件**
  C. 静态服务安全：不存在的文件 404、路径穿越拿不到仓库里的文件
  D. 与项目数据的联动：创建时带封面 / 编辑更换 / 编辑清空（传空串必须真的清空）
  E. 前端交互：上传区 → 选文件出预览 → 外链入口 → 移除后回到上传区 → 零 console 错误
  F. 旧文件回收：换封面 / 换成外链 / 清空时回收旧文件；共享引用不误删；哨兵文件不受影响
  G. 孤儿清扫脚本：干跑只报告不删、--apply 才删、被引用的封面绝不碰

用法（必须从仓库根目录跑）：python scripts/verify_cover_upload.py
"""
import json
import mimetypes
import os
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zlib

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
# 本轮上传产生的物理文件，结束时逐个删除（绝不整目录清空——那里可能有真实用户上传）
UPLOADED = []
# 脚本手工造的文件（哨兵 / 孤儿样本），同样在本轮结束时清掉
HANDMADE = []

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
BACKEND = os.path.join(REPO, "backend")
UPLOAD_DIR = os.path.join(BACKEND, "uploads", "projects")
TMP = os.path.join(os.environ.get("TEMP", "/tmp"), "_cover_verify")

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def path_of(url):
    """站内封面 URL -> 磁盘路径（用于断言文件到底在不在）"""
    return os.path.join(UPLOAD_DIR, url.rsplit("/", 1)[-1])


def exists(url):
    return os.path.exists(path_of(url))


def prune(*args):
    """跑一次清扫脚本，返回 (exitcode, stdout)"""
    proc = subprocess.run(
        ["node", "scripts/prune-uploads.js", *args],
        cwd=BACKEND,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def stale_file(name, days=2):
    """在磁盘上造一个「命名合法但没人引用、且已过宽限期」的孤儿文件"""
    p = os.path.join(UPLOAD_DIR, name)
    with open(p, "wb") as f:
        f.write(PNG_MAGIC + b"orphan")
    old = time.time() - days * 86400
    os.utime(p, (old, old))
    return name


# ---------------------------------------------------------------- 测试素材

def make_png(path, w=64, h=36):
    """造一张真的 PNG（不引第三方库，直接拼 IHDR/IDAT/IEND）"""
    raw = b""
    for _ in range(h):
        raw += b"\x00" + bytes([(x * 4) % 256 for x in range(w * 3)])

    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    with open(path, "wb") as f:
        f.write(PNG_MAGIC + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def make_text(path, content=b"this is definitely not an image"):
    with open(path, "wb") as f:
        f.write(content)


def dir_count():
    try:
        return len([n for n in os.listdir(UPLOAD_DIR) if os.path.isfile(os.path.join(UPLOAD_DIR, n))])
    except FileNotFoundError:
        return -1


# ---------------------------------------------------------------- 上传请求

def upload(token, path, field="file", ctype=None, filename=None):
    """手工拼 multipart/form-data（不依赖 requests，也不用外部 curl）-> (status, body)

    故意允许覆盖 ctype / filename：这正是「客户端声明的类型可以伪造」这一攻击面的入口。
    """
    boundary = "----coververify%d" % int(time.time() * 1000)
    filename = filename or os.path.basename(path)
    ctype = ctype or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    with open(path, "rb") as f:
        content = f.read()

    parts = [
        ("--%s\r\n" % boundary).encode(),
        ('Content-Disposition: form-data; name="%s"; filename="%s"\r\n' % (field, filename)).encode(),
        ("Content-Type: %s\r\n\r\n" % ctype).encode(),
        content,
        b"\r\n",
        ("--%s--\r\n" % boundary).encode(),
    ]
    req = urllib.request.Request(BASE + "/uploads/cover", data=b"".join(parts), method="POST")
    req.add_header("Content-Type", "multipart/form-data; boundary=%s" % boundary)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as err:
        raw = err.read()
        try:
            return err.code, json.loads(raw)
        except ValueError:
            return err.code, {"raw": raw.decode(errors="replace")}


def head_of(url):
    """返回 (status, content_type, size)"""
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            body = resp.read()
            return resp.status, resp.headers.get("Content-Type", ""), len(body)
    except urllib.error.HTTPError as err:
        return err.code, "", 0


def main():
    os.makedirs(TMP, exist_ok=True)
    ok_png = os.path.join(TMP, "original-cover-name.png")
    fake_png = os.path.join(TMP, "sneaky.png")
    big_png = os.path.join(TMP, "huge.png")
    plain_txt = os.path.join(TMP, "notes.txt")
    make_png(ok_png)
    make_text(fake_png)               # 扩展名是 .png，内容却是文本
    make_png(big_png)
    with open(big_png, "ab") as f:    # 撑到 6MB，超过 5MB 上限
        f.write(b"\x00" * (6 * 1024 * 1024))
    make_text(plain_txt)

    print("== A. 鉴权与成功路径 ==")
    status, _ = upload(None, ok_png)
    check("未登录上传被拒（401）", status == 401)

    user = register("cov")
    UIDS.append(user["uid"])
    token = user["token"]

    status, body = upload(token, ok_png)
    check("登录后上传合法 PNG 成功（200）", status == 200)
    url = body.get("data", {}).get("url", "")
    check(f"返回站内相对路径（{url}）", url.startswith("/uploads/projects/"))
    check("返回的不是带 host 的绝对地址（换域名不用改数据）", "http" not in url)
    # 服务端必须自己生成文件名：拿用户传来的名字落盘，等于把路径穿越和同名覆盖一起收下
    check("服务端重命名：返回的路径里没有原始文件名", "original-cover-name" not in url)
    name = url.rsplit("/", 1)[-1]
    UPLOADED.append(name)

    static_url = "http://localhost:5000" + url
    code, ctype, size = head_of(static_url)
    check(f"上传后能通过 /uploads 静态取到（{code} {ctype}）", code == 200 and "image/png" in ctype)
    check(f"取回的字节数与上传一致（{size}）", size == os.path.getsize(ok_png))

    print("\n== B. 校验边界（且被拒后不留垃圾文件）==")
    before = dir_count()

    status, body = upload(token, plain_txt)
    check("纯文本文件被拒（400）", status == 400)
    check(f"给出可读的格式说明（{body.get('message')}）", "JPG" in (body.get("message") or ""))

    # 关键一条：fileFilter 只看客户端声明的 MIME，而 MIME 是可以伪造的 ——
    # 必须靠文件头魔数兜住，否则「只支持图片」只是一句空话
    status, body = upload(token, fake_png, ctype="image/png")
    check("文本改名 .png 并声明 image/png，仍被拒（400）", status == 400)
    check(
        f"拒绝理由是「不是真正的图片」（{body.get('message')}）",
        "图片" in (body.get("message") or ""),
    )

    status, body = upload(token, big_png)
    check("超过 5MB 被拒（400）", status == 400)
    check(f"明确告知体积上限（{body.get('message')}）", "5MB" in (body.get("message") or ""))

    status, _ = upload(token, ok_png, field="avatar")
    check("字段名不叫 file 时被拒（400）", status == 400)

    check(f"三次被拒不曾在磁盘留下残留文件（{before} -> {dir_count()}）", dir_count() == before)

    print("\n== C. 静态服务安全 ==")
    code, _, _ = head_of("http://localhost:5000/uploads/projects/definitely-not-here.png")
    check("不存在的封面返回 404", code == 404)
    code, _, _ = head_of("http://localhost:5000/uploads/../package.json")
    check("路径穿越拿不到仓库文件（非 200）", code != 200)
    code, _, _ = head_of("http://localhost:5000/uploads/..%2f..%2fbackend%2fpackage.json")
    check("URL 编码的路径穿越同样拿不到（非 200）", code != 200)

    print("\n== D. 与项目数据的联动 ==")
    pid = api(
        "/projects",
        {
            "title": "封面验证项目",
            "description": "这是一条用于自动化验证临时创建的项目，验证结束后会被完整清理。",
            "categoryId": 1,
            "coverImage": url,
        },
        token=token,
    )["data"]["id"]
    PIDS.append(pid)

    detail = api(f"/projects/{pid}", token=token)["data"]
    check("创建时带上的封面被保存", detail["coverImage"] == url)
    check("详情读回的封面仍是可访问的", head_of("http://localhost:5000" + detail["coverImage"])[0] == 200)

    status, body = upload(token, ok_png)
    second = body["data"]["url"]
    UPLOADED.append(second.rsplit("/", 1)[-1])
    api(f"/projects/{pid}", {"coverImage": second}, token=token, method="PUT")
    check("编辑可更换封面", api(f"/projects/{pid}", token=token)["data"]["coverImage"] == second)

    # 传空串 = 清空。这一条容易在服务层被 `if (coverImage)` 吃掉，必须钉死
    api(f"/projects/{pid}", {"coverImage": ""}, token=token, method="PUT")
    check("传空串能真正清空封面（而不是被忽略）", not api(f"/projects/{pid}", token=token)["data"]["coverImage"])

    print("\n== F. 换 / 清封面时回收旧文件 ==")
    # 哨兵：命名合法、内容无所谓、时间新鲜。全程任何人都不该碰它 ——
    # 回收逻辑必须做到「只删自己那张旧图」，而不是顺手清目录
    sentinel_name = "1700000000123-5e171e100000.png"
    with open(os.path.join(UPLOAD_DIR, sentinel_name), "wb") as f:
        f.write(PNG_MAGIC + b"sentinel")
    HANDMADE.append(sentinel_name)

    status, body = upload(token, ok_png)
    a = body["data"]["url"]
    UPLOADED.append(a.rsplit("/", 1)[-1])
    api(f"/projects/{pid}", {"coverImage": a}, token=token, method="PUT")
    check("挂上第一张封面后文件确实在磁盘上", exists(a))

    status, body = upload(token, ok_png)
    b = body["data"]["url"]
    UPLOADED.append(b.rsplit("/", 1)[-1])
    api(f"/projects/{pid}", {"coverImage": b}, token=token, method="PUT")
    check("换封面后新文件已落盘", exists(b))
    check("换封面后旧文件被回收（以前这些会永久堆积，把磁盘吃满）", not exists(a))

    # 换成站外链接：站内那张旧图同样失去引用，应回收；外链本身不是磁盘上的东西
    ext = "https://example.com/some-cover.png"
    api(f"/projects/{pid}", {"coverImage": ext}, token=token, method="PUT")
    check("换成站外链接后，原站内文件被回收", not exists(b))
    check(
        "站外链接被原样保存（不被本地化或改写）",
        api(f"/projects/{pid}", token=token)["data"]["coverImage"] == ext,
    )

    # 共享引用保护：同一张图被两个项目引用时，改掉其中一个不能把图删了
    status, body = upload(token, ok_png)
    c = body["data"]["url"]
    UPLOADED.append(c.rsplit("/", 1)[-1])
    pid2 = api(
        "/projects",
        {
            "title": "封面共享引用验证项目",
            "description": "用于验证同一张封面被两个项目引用时不会被误删，验证结束即完整清理。",
            "categoryId": 1,
            "coverImage": c,
        },
        token=token,
    )["data"]["id"]
    PIDS.append(pid2)
    api(f"/projects/{pid}", {"coverImage": c}, token=token, method="PUT")

    api(f"/projects/{pid}", {"coverImage": ""}, token=token, method="PUT")
    check("其中一个项目清空后，仍被另一个引用的图不会被删", exists(c))

    api(f"/projects/{pid2}", {"coverImage": ""}, token=token, method="PUT")
    check("最后一个引用也清空后，图才被真正回收", not exists(c))

    check("哨兵文件全程未被误删（回收只针对自己那张旧图）", exists(sentinel_name))

    print("\n== G. 孤儿清扫脚本（捡回「上传了但没提交」的漏网文件）==")
    status, body = upload(token, ok_png)
    e = body["data"]["url"]
    UPLOADED.append(e.rsplit("/", 1)[-1])
    api(f"/projects/{pid}", {"coverImage": e}, token=token, method="PUT")
    e_name = e.rsplit("/", 1)[-1]

    old_orphan = stale_file("1700000000100-deadbeef0001.png", days=2)
    fresh_orphan = stale_file("1700000000101-deadbeef0002.png", days=0)
    HANDMADE.extend([old_orphan, fresh_orphan])

    code, out = prune()
    check("清扫脚本干跑正常退出（exit 0）", code == 0)
    check("过了宽限期的孤儿被列为候选", old_orphan in out)
    check("未过宽限期的未引用文件不被列为候选（避开「正在填表单」的竞态）", fresh_orphan not in out)
    check("被项目引用的封面不会被当成孤儿", e_name not in out)
    check("干跑不删除任何文件", exists(e) and os.path.exists(path_of("/uploads/projects/" + old_orphan)))

    code, out = prune("--min-age-hours=1", "--apply")
    check("加 --apply 才真的删（exit 0）", code == 0)
    check("过期孤儿被删除", not os.path.exists(path_of("/uploads/projects/" + old_orphan)))
    check("宽限期内（1h）的新鲜文件即使加了 --apply 也不动", os.path.exists(path_of("/uploads/projects/" + fresh_orphan)))
    check("被引用的封面在清扫后安然无恙", exists(e))

    print("\n== E. 前端交互 ==")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = attach(ctx.new_page())
        inject_login(page, token, user["user"])

        page.goto(f"{FRONT}/publish", wait_until="networkidle")
        page.wait_for_timeout(600)

        check("发布页有封面上传区", page.locator("[data-test='cover-drop']").count() == 1)
        check("初始没有预览图", page.locator("[data-test='cover-preview']").count() == 0)

        # 选择文件 -> 上传 -> 预览出现
        with page.expect_response("**/api/uploads/cover", timeout=15000):
            page.set_input_files("[data-test='cover-input']", ok_png)
        page.wait_for_selector("[data-test='cover-preview']", timeout=10000)
        check("选图后出现预览", page.locator("[data-test='cover-preview']").count() == 1)

        src = page.locator("[data-test='cover-preview'] img").get_attribute("src") or ""
        check(f"预览用的是站内上传地址（{src}）", src.startswith("/uploads/projects/"))
        # 前端这条路径同样在磁盘落了一个文件，必须一并追踪，否则每跑一轮就漏一个
        if src.startswith("/uploads/projects/"):
            UPLOADED.append(src.rsplit("/", 1)[-1])
        check("上传区已被预览取代", page.locator("[data-test='cover-drop']").count() == 0)
        check(
            "上传成功有提示",
            page.locator("[data-test^='toast-']").get_by_text("封面已上传").count() >= 1,
        )

        page.screenshot(path="docs/screenshots/cover-upload-light.png")
        page.emulate_media(color_scheme="dark")
        page.wait_for_timeout(500)
        page.screenshot(path="docs/screenshots/cover-upload-dark.png")
        page.emulate_media(color_scheme="light")

        # 外链兜底入口：不想上传文件的人也得有路走
        check("有「粘贴图片链接」兜底入口", page.locator("[data-test='cover-toggle-url']").count() == 1)
        page.click("[data-test='cover-toggle-url']")
        page.wait_for_timeout(200)
        check("点开后出现链接输入框", page.locator("[data-test='cover-url']").count() == 1)
        page.click("[data-test='cover-toggle-url']")
        page.wait_for_timeout(200)

        # 移除 -> 回到上传区（且传空串，后端必须真的清掉）
        page.click("[data-test='cover-remove']")
        page.wait_for_timeout(300)
        check("点移除后回到上传区", page.locator("[data-test='cover-drop']").count() == 1)
        check("点移除后预览消失", page.locator("[data-test='cover-preview']").count() == 0)

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
        # 只删本轮自己上传/自己造的文件，绝不整目录清空
        removed = 0
        targets = list(UPLOADED) + list(HANDMADE)
        for name in targets:
            try:
                os.remove(os.path.join(UPLOAD_DIR, name))
                removed += 1
            except OSError:
                pass
        left = dir_count()
        print(f"已清理临时数据（上传文件删除 {removed}/{len(targets)}，目录剩余 {left} 个）")
    finish()
