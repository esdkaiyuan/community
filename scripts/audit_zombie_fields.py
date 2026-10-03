# -*- coding: utf-8 -*-
"""僵尸字段扫描（只读，不改任何东西）

动机：Project.status 是「模型有声明、service 用白名单不取、前端拿不到」，
撞见才发现的。仓里可能还有同类 —— 这份脚本回答「哪些字段其实没在用」。

三问判据：
  1) 模型里有没有声明（models/*.js）
  2) service/controller/前端 有没有主动读写（排除 Sequelize 自动机制）
  3) 接口实际返回的 JSON 里有没有它
只有 1) 有、2)3) 都没有的，才是真僵尸。

用法（必须从仓库根目录跑）：
  "C:\\Users\\28916\\AppData\\Local\\Programs\\Python\\Python313\\python.exe" scripts/audit_zombie_fields.py

⚠️ 两个踩过的坑（别重犯）：
  · `sql()` 对 information_schema 的查询**返回 None**，取列名要用 GROUP_CONCAT 聚合成单值；
  · 接口取样**必须带 token**：/users/me、/notifications 未登录 401，取样会静默变空，
    把在用的字段误报成「接口不返回」（第一版就把 username/email 全误报了）。
    取样失败的表标 '?' 并**排除在僵尸判定之外**，不拿「没取到」当「没有」。
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _verify_common import api, cleanup_users, register, sql_one  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


def live_columns():
    """从线上库取全部表列（information_schema 走 GROUP_CONCAT 单值，sql() 取不到多行）。"""
    tables = sql_one(
        "SELECT GROUP_CONCAT(DISTINCT table_name) FROM information_schema.tables "
        "WHERE table_schema=DATABASE() AND table_type='BASE TABLE'"
    ) or ''
    out = {}
    for t in [x for x in tables.split(',') if x and x != 'migrations']:
        joined = sql_one(
            "SELECT GROUP_CONCAT(column_name ORDER BY ordinal_position SEPARATOR '|') "
            "FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='%s'" % t
        )
        if joined:
            out[t] = joined.split('|')
    return out


COLS = live_columns()

# Sequelize 的自动列 / 关联别名，不是「业务字段」
AUTO = {
    'id', 'created_at', 'updated_at', 'createdAt', 'updatedAt',
    'user_id', 'project_id', 'target_id',
}


def read(path):
    try:
        with open(path, encoding='utf-8') as f:
            return f.read()
    except OSError:
        return ''


# ---- 1) 模型里声明的字段 ----
model_decl = {}
mdir = os.path.join(REPO, 'backend', 'src', 'models')
MODEL_BY_TABLE = {
    'users': 'User.js', 'projects': 'Project.js', 'categories': 'Category.js',
    'project_comments': 'Comment.js', 'notifications': 'Notification.js',
    'activity_logs': 'ActivityLog.js', 'security_events': 'SecurityEvent.js',
    'project_favorites': 'ProjectFavorite.js', 'project_likes': 'ProjectLike.js',
    'project_participants': 'ProjectParticipant.js', 'project_views': 'ProjectView.js',
    'comment_likes': 'CommentLike.js',
}
for t, fn in MODEL_BY_TABLE.items():
    text = read(os.path.join(mdir, fn))
    # 顶层字段：形如 "  fieldName: {"（两空格缩进）
    for m in re.finditer(r'^  ([a-zA-Z_][a-zA-Z0-9_]*):\s*\{', text, re.M):
        col = m.group(1)
        if col in ('get', 'set'):
            continue
        model_decl.setdefault(t, set()).add(col)

# ---- 2) 业务代码里的读写 ----
SRC_DIRS = [
    os.path.join(REPO, 'backend', 'src'),
    os.path.join(REPO, 'frontend', 'src'),
]
code = {}
for d in SRC_DIRS:
    for root, _dirs, files in os.walk(d):
        if 'node_modules' in root:
            continue
        for f in files:
            if f.endswith(('.js', '.vue', '.ts')):
                p = os.path.join(root, f)
                if os.sep + 'models' + os.sep in p:
                    continue  # 模型声明不算「使用」
                code[p] = read(p)
code_blob = '\n'.join(code.values())

# ---- 3) 接口实际返回的字段 ----
# ⚠️ 必须带 token：/users/me、/notifications 未登录直接 401，取样会静默变成空 ->
#    把「在用的字段」误报成「接口不返回」。这轮第一次跑就踩了（username/email 全被误报）。
#    取样失败的表一律标成 '?'（未知），不参与僵尸判定。
returned = {}
SAMPLE_FAILED = set()


def sample(url, token, pick):
    try:
        d = api(url, token=token)
    except Exception:  # noqa: BLE001 - 取样失败 != 字段不存在
        return None
    data = (d or {}).get('data')
    return pick(data)


def pick_project(data):
    if isinstance(data, dict) and isinstance(data.get('projects'), list) and data['projects']:
        return set(data['projects'][0].keys())
    return None


def pick_flat(data):
    return set(data.keys()) if isinstance(data, dict) else None


def pick_list(data):
    for k in ('categories', 'logs', 'events', 'notifications'):
        if isinstance(data, dict) and isinstance(data.get(k), list) and data[k]:
            return set(data[k][0].keys())
    return None


# 登录态取样：/users/me 与 /notifications 必须带 token
_u = register('zombie_probe')
try:
    TOKEN = _u['token']
    _uid = _u['uid']
    _r = sample('/users/me', TOKEN, pick_flat)
    returned['users'] = _r if _r else set()
    if not _r:
        SAMPLE_FAILED.add('users')

    _r = sample('/projects?pageSize=1', None, pick_project)
    if _r:
        returned['projects'] = _r

    _r = sample('/notifications', TOKEN, pick_list)
    if _r:
        returned['notifications'] = _r

    _r = sample('/logs/me', TOKEN, pick_list)
    if _r:
        returned['activity_logs'] = _r

    _r = sample('/logs/me/security', TOKEN, pick_list)
    if _r:
        returned['security_events'] = _r
finally:
    cleanup_users([_uid])

# ---- 汇总 ----
# ---- 自检：取样本身有没有成功 ----
# 🔥 没有这一步，脚本会「安静地全绿」。第一版就因为 /users/me 未登录取样失败，
# 把 username / email / avatar / bio 全部误报成「接口不返回」——
# 一个只看「僵尸字段: 0 个」的结论是不可信的，必须先证明取样是有效的。
SELF_CHECK = [
    ('users', 'username'), ('users', 'email'), ('users', 'avatar'),
    ('projects', 'title'), ('projects', 'id'),
]
print('== 自检：取样是否有效 ==')
broken = []
for t, col in SELF_CHECK:
    ok = col in returned.get(t, set())
    print(('  OK  ' if ok else ' FAIL ') + f'{t}.{col} 出现在接口返回里')
    if not ok:
        broken.append(f'{t}.{col}')
if broken:
    print()
    print('!! 取样自检失败：' + ', '.join(broken))
    print('!! 说明接口取样没成功（未登录？后端没起？端点变了？）。')
    print('!! 这种情况下「僵尸字段」结论**不可信** —— 别把取样失败当成「字段没在用」。')
    sys.exit(1)

print()
print('== 扫描结果 ==')
print('%-18s %-22s %-6s %-6s %-6s' % ('表', '列', '模型', '代码', '接口'))
print('-' * 66)
zombies = []
for t in sorted(COLS):
    for col in COLS[t]:
        if col in AUTO:
            continue
        in_model = col in model_decl.get(t, set())
        # 驼峰也算（模型可能用驼峰映射到蛇形列）
        camel = re.sub(r'_([a-z])', lambda m: m.group(1).upper(), col)
        in_model = in_model or (camel in model_decl.get(t, set()))
        in_code = bool(re.search(r'\b' + re.escape(col) + r'\b', code_blob)) or \
            bool(re.search(r'\b' + re.escape(camel) + r'\b', code_blob))
        api_known = t not in SAMPLE_FAILED and t in returned
        in_api = (col in returned.get(t, set()) or camel in returned.get(t, set())) if api_known else True
        if in_model and not in_code and not in_api:
            zombies.append((t, col))
            print('%-18s %-22s %-6s %-6s %-6s' % (t, col, 'Y', '-', '-'))
        elif in_model and not in_api and in_code:
            print('%-18s %-22s %-6s %-6s %-6s  <- 代码在用但接口不返回' % (t, col, 'Y', 'Y', '-'))

print()
print('僵尸字段（模型声明、但代码与接口都不用）: %d 个' % len(zombies))
for t, c in zombies:
    print('   %s.%s' % (t, c))
if not zombies:
    print('   （无。注：这只说明「没有模型声明了却完全没人用的字段」，')
    print('     不代表遗留列已清理 —— 遗留列是「模型也没声明、但线上库里有」，')
    print('     另一份清单管那个，见 docs/遗留列处置决策清单.md）')
# 无需清理：列清单是运行时从 information_schema 现取的
