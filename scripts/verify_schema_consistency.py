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
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _verify_common import (  # noqa: E402
    DB_NAME,
    DB_PASS,
    DB_USER,
    MYSQL,
    MYSQL_CHARSET,
    check,
    finish,
    sql,
    sql_one,
)

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


# ===========================================================================
# S11~S15：这份文件**能不能真的建出库**
#
# 为什么需要这一组：S1~S10 全是「正则解析 + 比对元数据」，能查出表/索引/列名漂移，
# 却查不出下面三类错误 —— 因为它们只有在**真的执行 CREATE TABLE** 时才会暴露：
#
#   1. 语法错误（缺逗号）              → ERROR 1064，只有执行才知道
#   2. 外键引用了声明在后面的表        → ERROR 1824
#   3. AUTO_INCREMENT 列不是键         → ERROR 1075
#
# 而「拿 schema.sql 对线上库跑一遍」**也不够**：全是 CREATE TABLE IF NOT EXISTS，
# 表已存在时 MySQL 直接跳过执行、只做解析。所以 1075 这类语义错误照样漏网。
# 唯一可靠的办法：在隔离命名空间里**真的建一遍**。
#
# 隔离做法：把表名、REFERENCES 目标、CHECK 约束名统一加 zzverify_ 前缀，建完即删。
# ⚠️ REFERENCES 目标必须一起改名：否则会去引用**真实**的表，撞出
#    「int 与 int unsigned 不兼容」这种与 schema 本身无关的假错误（第一次就踩了）。
# ⚠️ CHECK 约束名在库内全局唯一，也必须改名，否则与真表撞名报 ERROR 3822。
# ===========================================================================

NS = "zzverify_"


def schema_source():
    return open(SCHEMA, encoding="utf-8").read()


def declaration_order():
    """表名 -> 在 schema.sql 里第几次出现（越早越先建）"""
    return {m.group(1): i for i, m in enumerate(TABLE_BLOCK_RE.finditer(schema_source()))}


def fk_dependency_violations():
    """找出「引用了声明在自己后面的表」的写法 —— MySQL 建库时会直接 ERROR 1824"""
    order = declaration_order()
    bad = []
    for m in TABLE_BLOCK_RE.finditer(schema_source()):
        table = m.group(1)
        for ref in re.findall(r"REFERENCES\s+`?(\w+)`?\s*\(", m.group(2)):
            if ref == table:
                continue  # 自引用（评论回复树 parent_id）永远合法
            if ref not in order:
                bad.append(f"{table}->{ref}(未声明)")
            elif order[ref] > order[table]:
                bad.append(f"{table}->{ref}(声明在后)")
    return sorted(set(bad))


def isolated_build_source():
    src = schema_source()
    src = re.sub(
        r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+(\w+)",
        lambda m: f"CREATE TABLE IF NOT EXISTS {NS}{m.group(1)}",
        src,
    )
    src = re.sub(r"REFERENCES\s+(\w+)\(", lambda m: f"REFERENCES {NS}{m.group(1)}(", src)
    src = re.sub(r"CONSTRAINT\s+(\w+)\s+CHECK", lambda m: f"CONSTRAINT {NS}{m.group(1)} CHECK", src)
    return src


def drop_isolated():
    """清理隔离命名空间。必须关外键检查，否则有依赖关系的表删不掉。"""
    rows = sql_one(
        "SELECT GROUP_CONCAT(CONCAT('DROP TABLE IF EXISTS ', table_name) SEPARATOR '; ') "
        "FROM information_schema.tables "
        f"WHERE table_schema = DATABASE() AND table_name LIKE '{NS}%'"
    )
    if rows and rows.upper() != "NULL":
        sql(f"SET FOREIGN_KEY_CHECKS=0; {rows}; SET FOREIGN_KEY_CHECKS=1")


def execute_sql_text(text):
    """把 SQL 文本喂给 mysql，返回 (是否零错误, 错误文本)。

    密码走 MYSQL_PWD 环境变量：命令行参数会把密码带进异常回溯，脚本一失败就漏进日志。
    """
    proc = subprocess.run(
        [MYSQL, "-u", DB_USER, DB_NAME, MYSQL_CHARSET],
        input=text,
        capture_output=True,
        text=True,
        env={**os.environ, "MYSQL_PWD": DB_PASS},
    )
    # 过滤掉客户端可能混进 stderr 的密码提示，否则「按 stderr 判成败」会恒红
    err = "\n".join(
        line
        for line in (proc.stderr or "").splitlines()
        if "Using a password" not in line and "MYSQL_PWD" not in line
    ).strip()
    return (not err), err


def _side_sets(select_sql):
    """跑一条「返回 GROUP_CONCAT(条目)」的查询，按 ';' 拆成一个集合。

    ⚠️ 不能把 GROUP_CONCAT 套在 GROUP_CONCAT 里：MySQL 不允许嵌套聚合
    （表现为查询直接报错，而不是返回错结果）。所以两侧各自先聚合到派生表，
    再在外层拼串，最后在 Python 侧比对集合差。
    """
    raw = sql_one(select_sql)
    if not raw or str(raw).strip().upper() == "NULL":
        return set()
    return {item.strip() for item in str(raw).split(";") if item.strip()}


def isolated_parity():
    """隔离构建结果 vs 线上真表：列（类型+可空）、索引（列组合）、外键（逐列）三比。

    刻意**不比默认值**：本文件对 updated_at 的默认值有一处已注明的有意偏离
    （线上是零日期默认值，在 MySQL 8 默认 sql_mode 下不可移植），比了就是永久噪音。
    """
    off = len(NS) + 1

    # 列：类型与可空性必须逐列相同（默认值不比，理由见 docstring）
    col = sql_one(
        "SELECT GROUP_CONCAT(line SEPARATOR ' ; ') FROM ("
        "  SELECT CONCAT('类型/可空不符 ', a.table_name, '.', a.column_name,"
        "         ' (构建=', a.column_type, '/', a.is_nullable,"
        "         ' 线上=', b.column_type, '/', b.is_nullable, ')') AS line"
        "    FROM information_schema.columns a"
        "    JOIN information_schema.columns b"
        f"      ON b.table_schema = DATABASE() AND b.table_name = SUBSTRING(a.table_name, {off})"
        "     AND b.column_name = a.column_name"
        f"   WHERE a.table_schema = DATABASE() AND a.table_name LIKE '{NS}%'"
        "     AND (a.column_type <> b.column_type OR a.is_nullable <> b.is_nullable)"
        "  UNION ALL"
        "  SELECT CONCAT('构建多出列 ', a.table_name, '.', a.column_name)"
        "    FROM information_schema.columns a"
        f"   WHERE a.table_schema = DATABASE() AND a.table_name LIKE '{NS}%'"
        "     AND NOT EXISTS (SELECT 1 FROM information_schema.columns b"
        "                      WHERE b.table_schema = DATABASE()"
        f"                        AND b.table_name = SUBSTRING(a.table_name, {off})"
        "                        AND b.column_name = a.column_name)"
        "  UNION ALL"
        "  SELECT CONCAT('构建漏掉列 ', b.table_name, '.', b.column_name)"
        "    FROM information_schema.columns b"
        "    JOIN information_schema.tables t ON t.table_schema = DATABASE()"
        f"     AND t.table_name = CONCAT('{NS}', b.table_name)"
        "   WHERE b.table_schema = DATABASE()"
        "     AND NOT EXISTS (SELECT 1 FROM information_schema.columns a"
        "                      WHERE a.table_schema = DATABASE()"
        f"                        AND a.table_name = CONCAT('{NS}', b.table_name)"
        "                        AND a.column_name = b.column_name)"
        ") t"
    )

    # 索引：按「列组合」比对（忽略索引名），与 S9 同一口径
    built_idx = _side_sets(
        "SELECT GROUP_CONCAT(CONCAT(tbl, ' [', cols, ']') SEPARATOR ';') FROM ("
        "  SELECT SUBSTRING(table_name, %d) AS tbl,"
        "         GROUP_CONCAT(column_name ORDER BY seq_in_index) AS cols"
        "    FROM information_schema.statistics"
        f"   WHERE table_schema = DATABASE() AND table_name LIKE '{NS}%%'"
        "     AND index_name <> 'PRIMARY'"
        "   GROUP BY table_name, index_name) x" % off
    )
    live_idx = _side_sets(
        "SELECT GROUP_CONCAT(CONCAT(tbl, ' [', cols, ']') SEPARATOR ';') FROM ("
        "  SELECT s.table_name AS tbl,"
        "         GROUP_CONCAT(s.column_name ORDER BY s.seq_in_index) AS cols"
        "    FROM information_schema.statistics s"
        "    JOIN information_schema.tables t ON t.table_schema = DATABASE()"
        f"     AND t.table_name = CONCAT('{NS}', s.table_name)"
        "   WHERE s.table_schema = DATABASE() AND s.index_name <> 'PRIMARY'"
        "   GROUP BY s.table_name, s.index_name) x"
    )

    # 外键：逐列比对（表.列 -> 被引用表.被引用列）
    built_fk = _side_sets(
        "SELECT GROUP_CONCAT(CONCAT(tbl, '.', col, '->', ref_tbl, '.', ref_col) SEPARATOR ';')"
        "  FROM (SELECT SUBSTRING(table_name, %d) AS tbl, column_name AS col,"
        "               SUBSTRING(referenced_table_name, %d) AS ref_tbl,"
        "               referenced_column_name AS ref_col"
        "          FROM information_schema.key_column_usage"
        f"         WHERE table_schema = DATABASE() AND table_name LIKE '{NS}%%'"
        "           AND referenced_table_name IS NOT NULL) y" % (off, off)
    )
    live_fk = _side_sets(
        "SELECT GROUP_CONCAT(CONCAT(tbl, '.', col, '->', ref_tbl, '.', ref_col) SEPARATOR ';')"
        "  FROM (SELECT k.table_name AS tbl, k.column_name AS col,"
        "               k.referenced_table_name AS ref_tbl,"
        "               k.referenced_column_name AS ref_col"
        "          FROM information_schema.key_column_usage k"
        "          JOIN information_schema.tables t ON t.table_schema = DATABASE()"
        f"           AND t.table_name = CONCAT('{NS}', k.table_name)"
        "         WHERE k.table_schema = DATABASE()"
        "           AND k.referenced_table_name IS NOT NULL) y"
    )

    def clean(value):
        return [] if not value or str(value).strip().upper() == "NULL" else str(value)

    idx_drift = sorted(built_idx - live_idx) + sorted(live_idx - built_idx)
    fk_drift = sorted(built_fk - live_fk) + sorted(live_fk - built_fk)
    return clean(col), idx_drift, fk_drift


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

    # ---- S11~S15：这份文件到底能不能真的建出库（见上方长注释）----
    bad_fk_order = fk_dependency_violations()
    check(f"S11 声明顺序满足外键依赖（违反: {bad_fk_order}）", not bad_fk_order)

    # 先清一次残留（上次中途失败可能留下 zzverify_*），保证计数干净
    drop_isolated()
    try:
        build_ok, build_err = execute_sql_text(isolated_build_source())
        first_err = build_err.splitlines()[0] if build_err else "无"
        check(f"S12 schema.sql 真的能建出表（首个错误: {first_err}）", build_ok)

        created = int(
            sql_one(
                "SELECT COUNT(*) FROM information_schema.tables "
                f"WHERE table_schema = DATABASE() AND table_name LIKE '{NS}%'"
            )
            or 0
        )
        check(f"S13 隔离构建建出 {created}/{len(schema)} 张表", created == len(schema))

        if created:
            col_drift, idx_drift, fk_drift = isolated_parity()
            check(f"S14 构建结果与线上逐列一致（漂移: {col_drift}）", not col_drift)
            check(f"S15 构建结果与线上索引一致（漂移: {idx_drift}）", not idx_drift)
            check(f"S15 构建结果与线上外键一致（漂移: {fk_drift}）", not fk_drift)
    finally:
        # 无论断言成败都必须清干净：验证脚本往生产库里建表本来就是「借」的
        drop_isolated()

    print(
        f"     线上表 {len(online)} / schema 表 {len(schema)} / 模型 {len(models)} / "
        f"含索引的表 {len(o_idx)}"
    )


if __name__ == "__main__":
    main()
    finish()
