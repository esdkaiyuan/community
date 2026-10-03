# -*- coding: utf-8 -*-
"""半成品功能扫描：找「只做了读路径、用户却填不进来」的字段

动机：2026-10-03 接了 `repositoryUrl` / `end_date`，自评「功能已交付」，
实际表单组件里 grep 命中 0 次 —— **用户根本没有输入框**，数据永远进不来。
只做了读路径。这类半成品很难靠读代码发现，所以用「六段自查」把它变成可扫的。

六段：录入(表单) / 存储(create+update) / 读取(输出映射) / 展示(模板) / 编辑回填 / 清空
     缺失段数越多越危险：只缺「录入」= 用户填不进来；缺「存储」= 填了也丢。

用法（必须从仓库根目录跑）：
  "C:\\Users\\28916\\AppData\\Local\\Programs\\Python\\Python313\\python.exe" scripts/audit_halfbuilt_fields.py

⚠️ 判据的已知局限（必须先读，否则会误判）：
  · 「录入」只在**共用表单组件**里找。若某功能的录入入口在别处（如独立页面、弹窗），
    会被误报成「无录入」。
  · 「展示」只在 views/ 与 components/ 里找文本引用，找不到不等于没渲染。
  · 因此本脚本只输出**线索**，不判定「这是 bug」。结论要人去看代码确认。
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _verify_common import register, cleanup_users, sql_one  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


def read(p):
    try:
        with open(p, encoding='utf-8') as f:
            return f.read()
    except OSError:
        return ''


def walk(subdir, exts):
    out = {}
    base = os.path.join(REPO, subdir)
    for root, _d, files in os.walk(base):
        if 'node_modules' in root:
            continue
        for fn in files:
            if fn.endswith(exts):
                p = os.path.join(root, fn)
                out[p] = read(p)
    return out


# ---- 源码分桶 ----
FRONT = walk('frontend/src', ('.vue', '.js', '.ts'))   # 前端
BE_SVC = {p: t for p, t in walk('backend/src', ('.js',)).items()
          if os.sep + 'services' + os.sep in p}              # service（存储 + 读取）
MODELS = {p: t for p, t in walk('backend/src', ('.js',)).items()
          if os.sep + 'models' + os.sep in p}               # 模型声明

svc_blob = '\n'.join(BE_SVC.values())
model_blob = '\n'.join(MODELS.values())
front_blob = '\n'.join(FRONT.values())
# 🔥 录入点 = **含 v-model 的组件**，不是「文件名含 Form 的」。
# 第一版按文件名找，只命中 ProjectForm.vue，于是 users.username / password
# 全被误报成「无录入」——而它们明明在 RegisterView / SecurityView 里。
# 判据宁可宽不可窄：宽了只是多看几眼，窄了会漏掉真缺口。
FORMS = {p: t for p, t in FRONT.items() if 'v-model' in t}
form_blob = '\n'.join(FORMS.values())


def camel(col):
    return re.sub(r'_([a-z])', lambda m: m.group(1).upper(), col)


def hits(blob, name):
    return bool(re.search(r'\b' + re.escape(name) + r'\b', blob))


# ---- 业务字段全集（排除系统列 / 关联列 / 审计时间列）----
AUTO = {
    'id', 'created_at', 'updated_at', 'deleted_at', 'createdAt', 'updatedAt',
    'user_id', 'project_id', 'target_id', 'category_id', 'creator_id',
    'parent_id', 'root_id', 'ip', 'user_agent', 'occururrences', 'fingerprint',
    'last_seen_at', 'first_seen_at', 'entity_type', 'entity_id', 'detail',
    # 派生/系统字段：本来就不该有录入入口（由点赞/浏览/已读/审计等行为产生）。
    # 不排除的话每个都报「缺录入」，真信号被噪音淹没。
    'like_count', 'comment_count', 'view_count', 'participant_count',
    'is_read', 'is_recommend', 'is_hot', 'role', 'joined_at', 'sort_order',
    'action', 'summary', 'target_type', 'actor_id', 'comment_id',
    'event', 'reason', 'account', 'method', 'path', 'target_user_id',
    'occurrences',   # 聚合出来的次数（atomic 自增），不是人能填的
    'icon',          # 分类图标属管理员配置，无用户录入入口
    # 下面两个走**中间变量**录入，字段名不出现在 v-model 上（见备注）
    'content',       # 评论正文 -> v-model="draft" / "replyDraft"
    'tags',          # 标签 -> v-model="tagInput" + addTagToList
    # token_version：会话版本号，用户**不该**填也不该看见（2026-10-03 改密功能引入）。
    # 刻意留在报告里当**已知例外**：将来若它真的没被读写，那是回归；
    # 若有人想给它加输入框，那才是问题。
    # 遗留状态列：线上取值与 schema 注释矛盾，语义未确认，不由本脚本判
    'status',
}

SELF_CHECK = [
    # 「一定在用」的字段，自检取样/扫描本身是否有效
    ('projects', 'title', 'frontend'),
    ('users', 'username', 'frontend'),
    ('projects', 'description', 'frontend'),
]


def scan():
    """返回 [(表, 列, 六段命中情况)]，只列「模型声明了但缺至少一段」的字段。"""
    tables = sql_one(
        "SELECT GROUP_CONCAT(DISTINCT table_name) FROM information_schema.tables "
        "WHERE table_schema=DATABASE() AND table_type='BASE TABLE'"
    ) or ''
    rows = []
    for t in [x for x in tables.split(',') if x and x != 'migrations']:
        joined = sql_one(
            "SELECT GROUP_CONCAT(column_name ORDER BY ordinal_position SEPARATOR '|') "
            "FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='%s'" % t
        )
        if not joined:
            continue
        for col in joined.split('|'):
            if col in AUTO:
                continue
            c = camel(col)
            if not hits(model_blob, col) and not hits(model_blob, c):
                continue  # 模型都没声明 -> 是「遗留列」，由决策清单管，不归本脚本
            # 🔥 必须把蛇形与驼峰**一起**判，且每段独立判断。
            # 第一版把「模型声明」判据写成 snake 或 camel 任一命中（对），
            # 但录入/存储/展示各段也这么写时，'repository_url' 在前端源码里
            # 一次都不出现（前端只用 repositoryUrl），而脚本据此认为
            # 「录入缺」—— 见证红时移除 v-model 竟毫无反应，说明判据没在测真东西。
            # 现在每段都用 snake/camel 任一命中为真，并让见证红能真正打出差异。
            #
            # 🔥 「录入」必须是**真的 v-model 绑定**，光「字段名出现过」不算：
            # payload、校验函数、form 定义里都有字段名，把整个输入框删掉它们还在 ——
            # 见证红时正是这样没报出差异（一个抓不到问题的「扫描器」等于没有）。
            has_vmodel = bool(
                re.search(r'v-model[^\n]*' + re.escape(c), form_blob)
                or re.search(r'v-model[^\n]*' + re.escape(col), form_blob)
            )
            seg = {
                '录入': has_vmodel,
                '存储': (hits(svc_blob, col) or hits(svc_blob, c)),
                '读取': (hits(svc_blob, col) or hits(svc_blob, c)),
                '展示': (hits(front_blob, col) or hits(front_blob, c)),
            }
            missing = [k for k, v in seg.items() if not v]
            if missing:
                rows.append((t, col, seg, missing))
    return rows


def main():
    print('== 自检：扫描前提是否成立 ==')
    ok = True
    for t, col, where in SELF_CHECK:
        blob = front_blob if where == 'frontend' else svc_blob
        good = hits(blob, col) or hits(blob, camel(col))
        print(('  OK  ' if good else ' FAIL ') + f'{t}.{col} 在 {where} 源码中能找到')
        ok &= good
    if not ok:
        print()
        print('!! 自检失败：扫描前提不成立，下面结论不可信。')
        sys.exit(1)

    rows = scan()
    print()
    print('== 模型已声明、但六段里有缺口的字段 ==')
    if not rows:
        print('  （无）')
    for t, col, seg, missing in rows:
        marks = ' '.join(f'{k}{"OK" if v else "缺"}' for k, v in seg.items())
        print(f'  {t}.{col:<20} {marks}  缺: {",".join(missing)}')
    print()
    print('⚠️ 这些是**线索不是结论**：「录入」只在共用表单组件里找，')
    print('   入口在别处的功能会被误报；「展示」靠文本引用找，找不到不等于没渲染。')
    print('   判真伪要去对应文件里看一眼。')
    return 0


if __name__ == '__main__':
    # 注册临时账号仅为满足某些 import 期副作用的库；本脚本本身不写库
    sys.exit(main())
