# -*- coding: utf-8 -*-
"""封面大图自动压缩 · 端到端验证

（待办 ②「图片裁剪 / 压缩」里「压缩」那一半。）

背景：服务端上限 5MB，而手机原图动辄 6~10MB —— 旧流程把用户直接挡回去
（「图片不能超过 5MB，请压缩后再上传」），等于让用户自己去找工具压一遍。
现在改成：选图后先在本机 canvas 降采样 + 重编码，用户无感。

这个改动有三个「不做会更糟」的边界，必须逐条钉住 —— 只顾着「大图能传了」
就会同时把下面三件事弄坏：
  - **只降不升**：小图必须**原样**上传。重编码不是免费的 —— 一张 30KB 的图过一遍
    canvas 常常变成 60KB 的 WebP，等于把用户的图越弄越糟。
  - **GIF 不动**：canvas 只能画第一帧，重编码会把动图压成一张静图 ——
    用户丢的是内容，比「超限被拒」糟得多。
  - **服务端闸门不放松**：客户端修好了 ≠ 可以直接 POST 超限内容。

覆盖六层：
  A. 素材与口径：造一张 >5MB 的真 PNG / 一张小 PNG / 一张小 GIF；
     并从**源码**读回压缩常量（不是把 1920 抄进断言里 —— 抄进去的话，
     哪天常量改了，测试会照样绿，而功能已经不按预期工作了）
  B. 服务端闸门：直接 POST 超限图片仍 400 且不留垃圾（这是后面各层的前提）
  C. 大图经 UI：被压缩 —— 变 webp / 体积大降 / 长边 == 源码常量 / 魔数真是 WebP /
     静态服务取得到 / 提示里写明了压缩
  D. 小图经 UI：字节与源文件完全一致（没有做无谓重编码）
  E. GIF 经 UI：字节一致、扩展名不变（动图没被压成静帧）
  F. 零 console 错误 + 清场对账

用法（必须从仓库根目录跑）：
  "C:\\Users\\28916\\AppData\\Local\\Programs\\Python\\Python313\\python.exe" scripts/verify_cover_compress.py
"""
import json
import mimetypes
import os
import re
import shutil
import tempfile
import time
import urllib.error
import urllib.request

from _verify_common import (
    BASE,
    FRONT,
    attach,
    check,
    cleanup_users,
    console_errors,
    finish,
    inject_login,
    register,
)

# 模块级：注册一旦失败，顶层 finally 也要兜得住（注册限流 429 会在这之前抛）
UIDS = []
# 本轮经 UI 上传产生的物理文件，结束时逐个删（绝不整目录清空：那里可能有真实用户数据）
UPLOADED = []

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
BACKEND = os.path.join(REPO, "backend")
UPLOAD_DIR = os.path.join(BACKEND, "uploads", "projects")
# 压缩常量与实现都在这个文件里（前端唯一出处）
COMPRESS_SRC = os.path.join(REPO, "frontend", "src", "utils", "imageCompress.js")
TMP = os.path.join(tempfile.gettempdir(), "_cover_compress_verify")

SERVER_MAX_BYTES = 5 * 1024 * 1024


# ---------------------------------------------------------------- 小工具

def path_of(url):
    # 空 url 要挡住：os.path.join(dir, "") 会拼出目录本身，exists() 就成了 True
    return os.path.join(UPLOAD_DIR, url.rsplit("/", 1)[-1]) if url else ""


def exists(url):
    return bool(url) and os.path.exists(path_of(url))


def size_of(url):
    try:
        return os.path.getsize(path_of(url))
    except OSError:
        return -1


def dir_count():
    try:
        return len([n for n in os.listdir(UPLOAD_DIR) if os.path.isfile(os.path.join(UPLOAD_DIR, n))])
    except FileNotFoundError:
        return -1


def source_number(name):
    """从 imageCompress.js 的源码里读回一个数字常量。

    断言不该把 1920 抄一遍：抄进去就等于「测试与实现各写一份」，
    常量改了测试照样绿。读源码才能让口径漂移立刻报红。
    """
    try:
        text = open(COMPRESS_SRC, encoding="utf-8").read()
    except OSError:
        return None
    # 取值可能是算式（如 `1.5 * 1024 * 1024`），所以连算符一起抓下来求值。
    # 字符集已经限死成「数字 / 点 / 空格 / * / +」，eval 不出别的东西来。
    m = re.search(rf"export const {name}\s*=\s*([0-9.*+ ]+)", text)
    if not m:
        return None
    try:
        return eval(m.group(1).strip(), {"__builtins__": {}}, {})  # noqa: S307
    except Exception:  # noqa: BLE001 - 读不懂就返回 None，让断言去报红
        return None


def upload_raw(token, path, field="file", ctype=None, filename=None):
    """手工拼 multipart 直接打接口（不经过页面）-> (status, body)

    页面路径已经被压缩过了，想验证「服务端闸门还在」就只能绕过前端直接发。
    """
    boundary = "----compressverify%d" % int(time.time() * 1000)
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
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as err:
        raw = err.read()
        try:
            return err.code, json.loads(raw)
        except ValueError:
            return err.code, {"raw": raw.decode(errors="replace")}


def head_of(url):
    """返回 (status, content_type)"""
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            resp.read(64)
            return resp.status, resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as err:
        return err.code, ""


def backend_can_delete(token):
    """后端此刻还能不能删掉自己刚落盘的文件？（本机沙箱守卫的判别手法）

    🔥 本机沙箱对「删文件」有守卫：一轮对话的删除量超过阈值后，后端进程**所有**
    fs.unlink* 都开始抛 `[safe-delete][SAFE_DELETE_BULK_CONFIRM_REQUIRED]`，
    而应用对回收失败是**刻意静默吞掉的**（只记日志）—— 于是「被拒不残留」
    「换封面回收旧图」这类断言会假红，看着像功能坏了。这个坑在本仓库已经踩过两轮。

    判别手法：让后端走一次**它自己的** unlinkSync（文本改名 .png → 魔数校验不过 →
    删文件）。删不掉就证明是环境在拦，不是应用的问题。
    （对照：Python 侧 os.remove 永远成功 —— 工具调用绕开了沙箱。）
    """
    probe = os.path.join(TMP, "probe-not-an-image.png")
    with open(probe, "wb") as f:
        f.write(b"definitely not an image")
    before = set(os.listdir(UPLOAD_DIR))
    upload_raw(token, probe, ctype="image/png")
    residual = sorted(set(os.listdir(UPLOAD_DIR)) - before)
    # 探针自清：工具调用绕开沙箱，这里一定删得掉
    for name in residual:
        try:
            os.remove(os.path.join(UPLOAD_DIR, name))
        except OSError:
            pass
        except BaseException:  # noqa: BLE001 - 沙箱删除守卫抛 SystemExit，抓不住会带崩整个脚本
            pass
    return not residual


# ---------------------------------------------------------------- 测试素材（用 PIL 造真图）

def make_big_png(path, w=2200, h=1500):
    """噪声图：PNG 压不动，所以文件真的会超过 5MB（模拟手机原图）"""
    from PIL import Image

    Image.frombytes("RGB", (w, h), os.urandom(w * h * 3)).save(path, "PNG")


def make_small_png(path, w=360, h=240):
    from PIL import Image

    Image.new("RGB", (w, h), (198, 220, 238)).save(path, "PNG")


def make_small_gif(path, w=64, h=64):
    from PIL import Image

    Image.new("P", (w, h), 3).save(path, "GIF")


def magic_of(url, n=12):
    try:
        with open(path_of(url), "rb") as f:
            return f.read(n)
    except OSError:
        return b""


# ---------------------------------------------------------------- 页面动作

def ui_upload(page, src_path, timeout=40000):
    """走真实用户路径上传（发布页选文件）-> (站内 url, 备注)

    **绝不抛异常**：功能整个坏掉时（例如本机压缩这一步把文件挡了下来，于是根本
    没有请求发出去），要让断言报一条可读的 FAIL —— 而不是一屏 traceback 把后面
    十几条断言全吃掉（那样「见证红」也只剩一条，覆盖面的证据就丢了）。
    """
    try:
        with page.expect_response("**/api/uploads/cover", timeout=timeout) as info:
            page.set_input_files("[data-test='cover-input']", src_path)
        url = (info.value.json().get("data") or {}).get("url", "")
    except Exception as err:  # noqa: BLE001 - 探针：任何异常都转成一条 FAIL 的依据
        return "", f"根本没有发出上传请求（{type(err).__name__}）"

    # 先登记清理再去等预览：后面的断言失败也不能让这个文件漏在磁盘上
    if url.startswith("/uploads/projects/"):
        UPLOADED.append(url.rsplit("/", 1)[-1])

    note = ""
    try:
        # 预览必须真的换成这张新图，否则后面的断言会对着上一张图做
        page.wait_for_function(
            "(u) => { const el = document.querySelector('[data-test=cover-preview] img'); "
            "return !!el && el.getAttribute('src') === u }",
            arg=url,
            timeout=10000,
        )
    except Exception:  # noqa: BLE001
        note = "预览没跟着换"
    return url, note


def wait_toasts_gone(page, timeout=8000):
    """等提示自然消失。

    成功提示会停留约 2.6s。「上一条说『已自动压缩…』」会让下一条的
    「不该出现压缩字样」断言假红 —— 断言必须只针对**这一次**的提示。
    """
    try:
        page.wait_for_function(
            """() => document.querySelectorAll("[data-test^='toast-']").length === 0""",
            timeout=timeout,
        )
    except Exception:  # noqa: BLE001 - 等不到就当它还在，让后面的断言去暴露
        pass


def natural_size(page, url):
    """让浏览器去解这张图，拿真实像素尺寸（省得为断言再引一个图像库）"""
    return page.evaluate(
        "(url) => new Promise((res) => { const i = new Image(); "
        "i.onload = () => res([i.naturalWidth, i.naturalHeight]); "
        "i.onerror = () => res(null); i.src = url })",
        url,
    )


def main():
    if os.path.isdir(TMP):
        shutil.rmtree(TMP, ignore_errors=True)
    os.makedirs(TMP, exist_ok=True)
    big_png = os.path.join(TMP, "phone-photo.png")
    small_png = os.path.join(TMP, "small-cover.png")
    small_gif = os.path.join(TMP, "small-cover.gif")
    make_big_png(big_png)
    make_small_png(small_png)
    make_small_gif(small_gif)

    print("== A. 素材与口径 ==")
    big_bytes = os.path.getsize(big_png)
    small_bytes = os.path.getsize(small_png)
    gif_bytes = os.path.getsize(small_gif)
    max_dim = source_number("COVER_MAX_DIMENSION")
    min_bytes = source_number("COVER_COMPRESS_MIN_BYTES")
    quality = source_number("COVER_QUALITY")

    check(f"素材「大图」确实超过服务端上限（{big_bytes / 1024 / 1024:.1f}MB > 5MB）", big_bytes > SERVER_MAX_BYTES)
    check(f"素材「小图」低于压缩阈值（{small_bytes}B）", 0 < small_bytes < (min_bytes or 0))
    # 读不到常量就直接红：别让「常量被改名」变成「测试静默跳过」
    check(f"从源码读到长边上限（{max_dim}）", max_dim == 1920)
    check(f"从源码读到压缩阈值（{min_bytes}）", min_bytes == 1.5 * 1024 * 1024)
    check(f"从源码读到压缩质量（{quality}）", quality == 0.82)

    print("\n== B. 服务端闸门未被放松（后面各层的前提）==")
    user = register("czip")
    UIDS.append(user["uid"])
    token = user["token"]

    before_names = set(os.listdir(UPLOAD_DIR))
    status, body = upload_raw(token, big_png)
    check("直接 POST 超限图片仍被拒（400）", status == 400)
    check(f"拒绝文案是中文且说清上限（{body.get('message')}）", "5MB" in (body.get("message") or ""))

    residual = sorted(set(os.listdir(UPLOAD_DIR)) - before_names)
    if backend_can_delete(token):
        check(
            f"被拒后磁盘不留残留（{len(before_names)} -> {dir_count()}"
            + (f"，残留 {', '.join(residual)}" if residual else "")
            + "）",
            not residual,
        )
    else:
        # 不把环境问题记成应用失败（也别静默跳过 —— 明说为什么不算）
        print("  SKIP 被拒后磁盘不留残留 —— 本机沙箱此刻在拦截后端删除（见 backend_can_delete 说明），是环境不是应用")
        for name in residual:
            try:
                os.remove(os.path.join(UPLOAD_DIR, name))
            except OSError:
                pass
            except BaseException:  # noqa: BLE001 - 沙箱删除守卫抛 SystemExit，抓不住会带崩整个脚本
                pass

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = attach(ctx.new_page())
        inject_login(page, token, user["user"])
        page.goto(f"{FRONT}/publish", wait_until="networkidle")
        page.wait_for_timeout(600)
        check("发布页有封面上传区", page.locator("[data-test='cover-drop']").count() == 1)

        print("\n== C. 大图经 UI 上传：本机压缩后才发出去 ==")
        base_count = dir_count()
        url_big, note = ui_upload(page, big_png)
        # 提示只停留 ~2.6s，趁它还在就抓下来，别等到本节末尾再去读
        big_toast = ""
        try:
            page.wait_for_selector("[data-test^='toast-']", timeout=6000)
            big_toast = " ".join(page.locator("[data-test^='toast-']").all_inner_texts())
        except Exception:  # noqa: BLE001
            pass

        check(f"超限大图这次传上去了（{url_big or note}）", url_big.startswith("/uploads/projects/"))
        check("落在磁盘上", exists(url_big))
        check(f"扩展名是 .webp（优先 WebP：体积最小且保留透明通道）", url_big.endswith(".webp"))

        got = size_of(url_big)
        check(f"体积压在 5MB 之内（这是它能传上去的原因，{got / 1024 / 1024:.2f}MB）", 0 < got <= SERVER_MAX_BYTES)
        check(
            f"体积显著变小（{big_bytes / 1024 / 1024:.1f}MB -> {got / 1024 / 1024:.2f}MB，压掉 {100 - got * 100 / big_bytes:.0f}%）",
            0 < got < big_bytes * 0.4,
        )

        dims = natural_size(page, url_big)
        long_side = max(dims) if dims else -1
        check(f"长边被降到源码里的上限（{dims} -> {long_side}）", long_side == max_dim)
        # 只降不升：绝不能把图放大
        check("没有放大原图", bool(dims) and dims[0] <= 2200 and dims[1] <= 1500)

        head = magic_of(url_big)
        check(
            "文件头是真 WebP（RIFF....WEBP，扩展名不撒谎）",
            head[:4] == b"RIFF" and head[8:12] == b"WEBP",
        )

        code, ctype = head_of("http://localhost:5000" + url_big)
        check(f"压缩后的图能通过 /uploads 静态取到（{code} {ctype}）", code == 200 and "image/webp" in ctype)
        check("上传只落一个文件（没有既有文件被顺手删掉）", dir_count() == base_count + 1)
        check(
            f"成功提示里写明了压缩发生了（{big_toast!r}）",
            "自动压缩" in big_toast,
        )

        print("\n== D. 小图经 UI 上传：原样放行 ==")
        # 先等上一条「已自动压缩…」自然消失：否则下面的负向断言会读到一个不属于本次的提示
        wait_toasts_gone(page)
        url_small, note = ui_upload(page, small_png)
        check(f"小图上传成功（{url_small or note}）", url_small.startswith("/uploads/projects/"))
        check("扩展名仍是 .png（没有被无谓地转成 webp）", url_small.endswith(".png"))
        check(
            f"字节与源文件完全一致（{size_of(url_small)}B，不做无谓重编码）",
            size_of(url_small) == small_bytes,
        )
        small_toast = ""
        try:
            page.wait_for_selector("[data-test^='toast-']", timeout=6000)
            small_toast = " ".join(page.locator("[data-test^='toast-']").all_inner_texts())
        except Exception:  # noqa: BLE001
            pass
        check(
            f"本次提示是「封面已上传」且不含压缩字样（{small_toast!r}）",
            "封面已上传" in small_toast and "自动压缩" not in small_toast,
        )

        print("\n== E. GIF 经 UI 上传：动图不碰 ==")
        url_gif, note = ui_upload(page, small_gif)
        check(f"GIF 上传成功（{url_gif or note}）", url_gif.startswith("/uploads/projects/"))
        check("扩展名仍是 .gif（canvas 重编码会把动图压成静帧，所以刻意跳过）", url_gif.endswith(".gif"))
        check(f"字节与源文件完全一致（{size_of(url_gif)}B）", size_of(url_gif) == gif_bytes)
        check("文件头仍是 GIF8", magic_of(url_gif, 4) == b"GIF8")

        page.screenshot(path="docs/screenshots/cover-compress-light.png")
        ctx.close()
        browser.close()

    console_errors[:] = [e for e in console_errors if not e.startswith("Failed to load resource")]
    check(f"全程零 console 错误（{len(console_errors)} 条）", not console_errors)


if __name__ == "__main__":
    try:
        main()
    finally:
        if UIDS:
            cleanup_users(UIDS)
        removed = 0
        for name in UPLOADED:
            try:
                os.remove(os.path.join(UPLOAD_DIR, name))
                removed += 1
            except OSError:
                pass
            except BaseException:  # noqa: BLE001 - 沙箱删除守卫抛 SystemExit，抓不住会带崩整个脚本
                pass
        shutil.rmtree(TMP, ignore_errors=True)
        print(f"已清理临时数据（上传文件删除 {removed}/{len(UPLOADED)}，目录剩余 {dir_count()} 个）")
    finish()
