#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""验证脚本的数据库连接配置。

⚠️ 为什么单独抽这一个文件：这些脚本曾经把**生产数据库密码硬编码**在里面，
而本仓库是公开的（GitHub: esdkaiyuan/community）。密码一旦提交进 git 历史，
即使之后删掉，历史里依然可读 —— 只能靠**轮换密码**来止损。
所以规则只有一条：**凭据只能来自环境变量或 backend/.env（.gitignore 已忽略），
任何源码文件里都不许出现密码字面量。**

读取优先级：
  1. 环境变量 VERIFY_DB_USER / VERIFY_DB_PASS / VERIFY_DB_NAME
  2. backend/.env 里的 DB_USER / DB_PASSWORD / DB_NAME
  3. 非敏感的默认值（用户名/库名本身就是公开信息，密码没有默认值）
"""

import os

_ENV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", ".env"
)


def dotenv_value(key, default=""):
    """从 backend/.env 读一个键。读不到就返回 default（不抛异常）。"""
    try:
        with open(_ENV_PATH, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                name, value = line.split("=", 1)
                if name.strip() == key:
                    return value.strip()
    except OSError:
        pass
    return default


DB_USER = os.environ.get("VERIFY_DB_USER") or dotenv_value("DB_USER", "co_creation_esdk")
DB_NAME = os.environ.get("VERIFY_DB_NAME") or dotenv_value("DB_NAME", "co_creation_esdk")
# 密码没有兜底默认值：拿不到就是空串，让连接直接失败并暴露出来，
# 好过悄悄用一个人人可见的默认密码连上生产库。
DB_PASS = os.environ.get("VERIFY_DB_PASS") or dotenv_value("DB_PASSWORD", "")
