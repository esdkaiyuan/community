#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""钉死「schema.sql ↔ 线上库 ↔ Sequelize 模型」三方一致。

为什么需要它：审计发现 schema.sql 声明 14 张表、线上实际只有 12 张 ——
`tags` 与 `project_tags` 从未被创建过，也从未被任何 service 引用（真实标签
只存 projects.tags 这个 JSON 列），但 models/ 里还留着 Tag / ProjectTag 两个
模型并在 index.js 注册。这类漂移不会报错、不会崩，只会一直误导后来的人
（「标签明明有关系表啊」），等到真要做标签治理时才发现无表可用。

本脚本把「三方一致」变成可执行的不变量：
  1. schema.sql 声明的表集合 == 线上表集合（双向，不多不少）
  2. 每个模型声明的 tableName 在线上库里真的存在
  3. 线上每张表都有模型对应（防止反向漂移：建了表却没人管）
  4. models/index.js 导出的模型 == models/ 下的模型文件（不含 index.js）
  5. 模型文件都被 index.js 注册（防止「建了模型忘了挂」）

运行（仓库根目录）：
  "C:/Users/28916/AppData/Local/Programs/Python/Python313/python.exe" scripts/verify_schema_consistency.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _verify_common import check, finish, sql_one  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(ROOT, "backend", "database", "schema.sql")
MODELS_DIR = os.path.join(ROOT, "backend", "src", "models")
MODELS_INDEX = os.path.join(MODELS_DIR, "index.js")


def online_tables():
    rows = sql_one(
        "SELECT GROUP_CONCAT(table_name) FROM information_schema.tables "
        "WHERE table_schema = DATABASE()"
    )
    if not rows or str(rows).strip().upper() == "NULL":
        return set()
    return {t for t in str(rows).split(",") if t}


def schema_tables():
    src = open(SCHEMA, encoding="utf-8").read()
    # 只取建表语句，忽略注释里的示范与文档片段
    return set(re.findall(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?", src))


def model_table_map():
    """模型文件名 -> 声明的 tableName（没有显式声明则按 Sequelize 默认复数推导）"""
    out = {}
    for name in os.listdir(MODELS_DIR):
        if not name.endswith(".js") or name == "index.js":
            continue
        src = open(os.path.join(MODELS_DIR, name), encoding="utf-8").read()
        m = re.search(r"tableName:\s*['\"](\w+)['\"]", src)
        if m:
            out[name[:-3]] = m.group(1)
        else:
            # 兜底：Sequelize 默认把模型名转成复数形式的表名
            base = name[:-3]
            out[base] = (base + "s").lower()
    return out


def index_exports():
    src = open(MODELS_INDEX, encoding="utf-8").read()
    m = re.search(r"module\.exports\s*=\s*\{(.*?)\}", src, re.S)
    if not m:
        return set()
    body = m.group(1)
    return {x.strip() for x in body.split(",") if x.strip()}


def main():
    online = online_tables()
    schema = schema_tables()
    models = model_table_map()
    exports = index_exports()

    check("S1 线上库非空（探针本身没瞎）", len(online) > 0)

    # 1. schema 与线上双向一致
    only_schema = sorted(schema - online)
    only_online = sorted(online - schema)
    check(
        f"S2 schema.sql 声明的表在线上都存在（多出: {only_schema}）",
        not only_schema,
    )
    check(
        f"S3 线上表都在 schema.sql 里声明（缺失: {only_online}）",
        not only_online,
    )
    check(
        f"S4 两方表数一致（schema={len(schema)} 线上={len(online)}）",
        len(schema) == len(online),
    )

    # 2. 每个模型指向的表都真实存在
    missing = sorted({t for t in models.values() if t not in online})
    check(f"S5 模型指向的表在线上都存在（缺失: {missing}）", not missing)

    # 3. 线上每张表都有模型（反向漂移）
    covered = set(models.values())
    orphan_tables = sorted(online - covered)
    check(
        f"S6 线上表都有模型对应（孤儿表: {orphan_tables}）",
        not orphan_tables,
    )

    # 4/5. 模型文件与 index.js 注册一致
    model_names = set(models.keys())
    check(
        f"S7 index.js 未导出不存在的模型（多余: {sorted(exports - model_names - {'sequelize'})}）",
        not (exports - model_names - {"sequelize"}),
    )
    check(
        f"S8 模型文件都被 index.js 注册（漏挂: {sorted(model_names - exports)}）",
        not (model_names - exports),
    )

    # 附加：把结论打印出来，人工也能一眼看
    print(f"     线上表 {len(online)} 张 / schema 声明 {len(schema)} 张 / 模型 {len(models)} 个")


if __name__ == "__main__":
    main()
    finish()
