# -*- coding: utf-8 -*-
"""verify_*.py 套件运行器（本地与 CI 共用，接入 GitHub Actions 的一环）

职责：
- 服务自举：后端 / 前端没起就拉起并等健康；已经在跑就直接复用（不动本机现役服务）
- 顺序跑全部 verify_*.py + audit_frontend_ui.py，逐个记录 exit code
- 运行器自己拉起的后端，在每个脚本之间重启一次以清零限流计数器
  （uploadLimiter 40 次 / 15 分钟：封面压缩 + 裁剪 + 上传三个脚本就够摸到上限）；
  复用的现役服务则不碰——那是本机开发会话，重启权不归套件
- 全部跑完后打印汇总，任一失败 exit 1（CI 以此判定红绿）

用法（必须从仓库根目录跑）：
  python scripts/run_verify_suite.py                    # 全量
  python scripts/run_verify_suite.py --only a,b         # 只跑指定脚本（.py 后缀可省）
  python scripts/run_verify_suite.py --list             # 只打印将运行的脚本清单
  python scripts/run_verify_suite.py --no-restart       # 明确禁止脚本间重启后端

⚠️ 解释器：脚本用 sys.executable（即启动套件的那个 python）执行——它必须装有
playwright。本地缺省的 python 没有 playwright，请用完整路径解释器启动本套件，
或设 VERIFY_PYTHON 显式指定；CI 里 setup-python 装好 playwright 后 sys.executable
天然正确。

CI 环境（见 .github/workflows/verify.yml）：DB_* 指向 service MySQL，
VERIFY_MYSQL_CLI=mysql（linux 的 mysql 在 PATH 里），playwright + chromium 预装。
"""
import argparse
import glob
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

BASE_HEALTH = os.environ.get("VERIFY_API_BASE", "http://localhost:5000/api") + "/categories"
FRONT_URL = os.environ.get("VERIFY_FRONT_BASE", "http://localhost:3001") + "/"
SCRIPT_TIMEOUT = 1200  # 单脚本 20 分钟封顶（最重的是封面裁剪 + 全站巡检）
# 脚本解释器：必须带 playwright（见 docstring ⚠️）；CI 里 setup-python 的 python 天然满足
SCRIPT_PY = os.environ.get("VERIFY_PYTHON") or sys.executable


def http_ok(url):
    """可达且非 5xx 即算健康（404 也算服务在）"""
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status < 500
    except urllib.error.HTTPError:
        return True  # 有 HTTP 响应就是服务在
    except Exception:
        return False


def wait_ready(url, timeout=60.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if http_ok(url):
            return True
        time.sleep(0.5)
    return False


def spawn_backend():
    """拉起后端（继承当前环境：CI 的 DB_* 变量由此传入；本地则 backend/.env 兜底）"""
    node = os.environ.get("NODE_BIN", "node")
    log = open(os.path.join("backend", "suite-server.log"), "ab")
    proc = subprocess.Popen(
        [node, "server.js"],
        cwd="backend",
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    if not wait_ready(BASE_HEALTH):
        proc.terminate()
        raise RuntimeError("后端拉起后 60s 未通过健康检查（backend/suite-server.log 有日志）")
    return proc


def spawn_frontend():
    """拉起 vite dev（端口 3001 由 vite.config.js 固定，与 _verify_common.FRONT 对齐）"""
    node = os.environ.get("NODE_BIN", "node")
    vite_js = os.path.join("frontend", "node_modules", "vite", "bin", "vite.js")
    proc = subprocess.Popen(
        [node, vite_js],
        cwd="frontend",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if not wait_ready(FRONT_URL):
        proc.terminate()
        raise RuntimeError("前端拉起后 60s 未就绪（确认 frontend/node_modules 已安装）")
    return proc


def restart_backend(backend_proc):
    """重启后端清限流（仅对运行器自己拉起的进程）；跨平台终止单个 node 进程"""
    backend_proc.terminate()
    try:
        backend_proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        backend_proc.kill()
    time.sleep(1)
    return spawn_backend()


def collect_scripts(only):
    """全量 = verify_*.py（字典序）+ audit_frontend_ui.py 收尾；--only 过滤"""
    names = sorted(os.path.basename(p) for p in glob.glob("scripts/verify_*.py"))
    names.append("audit_frontend_ui.py")
    if only:
        wanted = {n if n.endswith(".py") else f"{n}.py" for n in only}
        missing = wanted - set(names)
        if missing:
            raise SystemExit(f"--only 里有不存在的脚本: {sorted(missing)}")
        names = [n for n in names if n in wanted]
    return names


def main():
    parser = argparse.ArgumentParser(description="跑 verify 套件")
    parser.add_argument("--only", default="", help="逗号分隔的脚本名（.py 可省）")
    parser.add_argument("--list", action="store_true", help="只打印清单")
    parser.add_argument("--no-restart", action="store_true", help="脚本间不重启后端")
    args = parser.parse_args()

    names = collect_scripts([s for s in args.only.split(",") if s])
    if args.list:
        print("\n".join(names))
        print(f"共 {len(names)} 个脚本")
        return

    owned_backend = None
    owned_frontend = None
    try:
        if http_ok(BASE_HEALTH):
            print("后端已在跑，直接复用（脚本间不重启）")
        else:
            print("拉起后端 ...")
            owned_backend = spawn_backend()
        if http_ok(FRONT_URL):
            print("前端已在跑，直接复用")
        else:
            print("拉起前端（vite dev :3001）...")
            owned_frontend = spawn_frontend()

        restart_allowed = (not args.no_restart) and owned_backend is not None
        results = []
        for i, name in enumerate(names):
            if i > 0 and restart_allowed:
                print("\n-- 重启后端清限流 --")
                owned_backend = restart_backend(owned_backend)
            print(f"\n===== [{i + 1}/{len(names)}] {name} =====")
            proc = subprocess.run(
                [SCRIPT_PY, os.path.join("scripts", name)],
                timeout=SCRIPT_TIMEOUT,
            )
            results.append((name, proc.returncode))
            print(f"----- {name} EXIT={proc.returncode} -----")

        print("\n========== 汇总 ==========")
        failed = 0
        for name, rc in results:
            mark = "PASS" if rc == 0 else "FAIL"
            failed += rc != 0
            print(f"  {mark}  {name}")
        print(f"共 {len(results)} 个脚本，{failed} 个失败")
        sys.exit(1 if failed else 0)
    finally:
        # 运行器拉起的服务留给 CI 生命周期收尾；本地复用场景更不能动
        pass


if __name__ == "__main__":
    main()
