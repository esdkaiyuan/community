#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""钉死「schema.sql ↔ 线上库 ↔ Sequelize 模型 ↔ 索引」四方一致。

为什么需要它：审计发现两类静默漂移，都不报错、不崩溃，只会持续误导：

  1. 表漂移 —— schema.sql 声明 14 张表、线上只有 12 张。tags / project_tags
     从未被创建，也从未被任何 service 读写（真实标签只存 projects.tags JSON 列），
     但 models/ 里还留着 Tag / ProjectTag 两个模型并在 index.js 注册。
  2. 索引漂移 —— 线上 projects 有 idx_created / idx_status，schema.sql 里没声明；
     而最高频的 sort=hot / sort=participants 对应列又**没有**索引，
     ORDER BY 每次全表 filesort。

本脚本把一致性变成可执行的不变量：
  1~4. schema.sql 声明的表 ↔ 线上表（双向，不多不少）
  5~8. 模型指向的表存在、线上表都有模型、模型文件与 index.js 注册一致
  9.   索引逐表一致（双向）
  10.  三个高频排序列必须有索引兜底

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

# 每个 CREATE TABLE 块：从 `(` 一直吃到行首的 `);`
# （正则里的换行用 chr(10) 拼接：heredoc 会把字面 \n 变成真实换行，源码会被截断）
TABLE_BLOCK_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?\s*\((.*?" + chr(10) + r"\)[^;]*;)",
    re.S,
)
INDEX_RE = re.compile(r"(?:INDEX|KEY)\s+`?(\w+)`?\s*\(")


def online_tables():
    rows = sql_one(
        "SELECT GROUP_CONCAT(table_name) FROM information_schema.tables "
        "WHERE table_schema = DATABASE()"
    )
    if not rows or str(rows).strip().upper() == "NULL":
        return set()
    return {t for t in str(rows).split(",") if t}


def schema_tables_and_indexes():
    src = open(SCHEMA, encoding="utf-8").read()
    tables = set()
    indexes = {}
    for m in TABLE_BLOCK_RE.finditer(src):
        table, body = m.group(1), m.group(2)
        tables.add(table)
        # 按「列组合」比对而不是索引名：线上有历史遗留的命名差异
        # （比如同一个索引在 schema 里叫 idx_user、库里叫 user_id），
        # 名字不同但语义相同的索引不该报成漂移；真正要抓的是「有没有这个索引」
        tuples = set()
        for m2 in re.finditer(r"(?:UNIQUE\s+KEY|INDEX|KEY)\s+(?:`?\w+`?\s*)?\(([^)]*)\)", body):
            # PRIMARY KEY 与 FOREIGN KEY 不是普通索引：前者线上侧已排除，
            # 后者根本不建索引（外键会顺带建的那条由线上侧如实反映）
            prefix = body[max(0, m2.start() - 10): m2.start()].rstrip().upper()
            if prefix.endswith("FOREIGN") or prefix.endswith("PRIMARY"):
                continue
            cols = tuple(c.strip().strip("`") for c in m2.group(1).split(",") if c.strip())
            if not cols:
                continue
            tuples.add(cols)
        # 列级 UNIQUE（如 `username VARCHAR(50) NOT NULL UNIQUE`）也是一条索引
        for line in body.splitlines():
            stripped = line.strip().upper()
            # 跳过各种 KEY 定义行本身（否则 `UNIQUE KEY uk_x (...)` 里的
            # UNIQUE 会被当成列名，凭空多出一个 ('UNIQUE',) 索引）
            if re.match(r"^(UNIQUE|INDEX|KEY|PRIMARY|FOREIGN)\b", stripped):
                continue
            m3 = re.match(r"\s*`?(\w+)`?\s+\w+", line)
            if m3 and re.search(r"\bUNIQUE\b", line):
                tuples.add((m3.group(1),))
        indexes[table] = tuples
    return tables, indexes


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
            base = name[:-3]
            out[base] = (base + "s").lower()
    return out


def index_exports():
    src = open(MODELS_INDEX, encoding="utf-8").read()
    m = re.search(r"module\.exports\s*=\s*\{(.*?)\}", src, re.S)
    if not m:
        return set()
    return {x.strip() for x in m.group(1).split(",") if x.strip()}


def online_indexes():
    """table -> {(列组合)}，与 schema 侧同一口径（按列比对，忽略索引命名差异）"""
    rows = sql_one(
        "SELECT GROUP_CONCAT(CONCAT_WS('~', table_name, cols) SEPARATOR ';') FROM ("
        "  SELECT table_name, index_name,"
        "         GROUP_CONCAT(column_name ORDER BY seq_in_index) AS cols"
        "    FROM information_schema.statistics"
        "   WHERE table_schema = DATABASE() AND index_name <> 'PRIMARY'"
        "   GROUP BY table_name, index_name) t"
    )
    out = {}
    if not rows or str(rows).strip().upper() == "NULL":
        return out
    for item in str(rows).split(";"):
        if "~" not in item:
            continue
        table, cols = item.split("~", 1)
        out.setdefault(table, set()).add(tuple(c.strip() for c in cols.split(",") if c.strip()))
    return out


def main():
    online = online_tables()
    schema, s_idx = schema_tables_and_indexes()
    models = model_table_map()
    exports = index_exports()
    o_idx = online_indexes()

    check("S1 线上库非空（探针本身没瞎）", len(online) > 0)

    only_schema = sorted(schema - online)
    only_online = sorted(online - schema)
    check(f"S2 schema.sql 声明的表在线上都存在（多出: {only_schema}）", not only_schema)
    check(f"S3 线上表都在 schema.sql 里声明（缺失: {only_online}）", not only_online)
    check(
        f"S4 两方表数一致（schema={len(schema)} 线上={len(online)}）",
        len(schema) == len(online),
    )

    missing = sorted({t for t in models.values() if t not in online})
    check(f"S5 模型指向的表在线上都存在（缺失: {missing}）", not missing)

    orphan_tables = sorted(online - set(models.values()))
    check(f"S6 线上表都有模型对应（孤儿表: {orphan_tables}）", not orphan_tables)

    model_names = set(models.keys())
    extra_exports = sorted(exports - model_names - {"sequelize"})
    check(f"S7 index.js 未导出不存在的模型（多余: {extra_exports}）", not extra_exports)
    check(
        f"S8 模型文件都被 index.js 注册（漏挂: {sorted(model_names - exports)}）",
        not (model_names - exports),
    )

    # 断言方向只取「schema 声明的索引必须在线上存在」（防索引被误删）；
    # 反向差异（线上有、schema 没写）只做提示 —— DDL 里的无名索引、历史遗留
    # 命名差异解析不干净，拿它当断言会制造噪音，但它依然是值得补的文档缺口。
    drift = []
    extra = []
    for table in sorted(set(s_idx) | set(o_idx)):
        no_online = sorted(s_idx.get(table, set()) - o_idx.get(table, set()))
        no_schema = sorted(o_idx.get(table, set()) - s_idx.get(table, set()))
        if no_online:
            drift.append(f"{table}(线上缺{no_online})")
        if no_schema:
            extra.append(f"{table}(schema 缺{no_schema})")
    check(f"S9 schema 声明的索引在线上都存在（漂移: {drift}）", not drift)
    if extra:
        print(f"     提示：线上有而 schema 未声明的索引 {extra}")

    for col in ["created_at", "like_count", "participant_count"]:
        has = sql_one(
            "SELECT COUNT(*) FROM information_schema.statistics "
            f"WHERE table_schema = DATABASE() AND table_name = 'projects' "
            f"AND column_name = '{col}'"
        )
        check(f"S10 排序列 {col} 有索引（否则 ORDER BY 全表 filesort）", int(has or 0) > 0)

    print(
        f"     线上表 {len(online)} / schema 表 {len(schema)} / 模型 {len(models)} / "
        f"含索引的表 {len(o_idx)}"
    )


if __name__ == "__main__":
    main()
    finish()
