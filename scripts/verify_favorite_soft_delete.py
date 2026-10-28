# -*- coding: utf-8 -*-
"""收藏与软删除的一致性验证

背景：`projects` 是 paranoid 软删除（`deleted_at`），而 `project_favorites` 外键的
`ON DELETE CASCADE` 只在**物理删除**时触发。于是项目被软删后收藏关系行仍留在表里，
两个计数口径就分叉了：

  - `/users/me/favorites` 的 `total` 来自未过滤的 count，列表却 `.filter(row => row.project)`
    过滤掉软删项目 -> 数字与条数对不上，且「加载更多」永远显示
  - `/users/me/stats` 的 `favoriteCount` 直接 `ProjectFavorite.count`，把软删项目算进去

覆盖：
1) 正常路径：收藏 1 个未删项目 -> total / 条数 / favoriteCount 三者一致
2) 软删后：total 与条数仍一致（都为 0），favoriteCount 不再虚高
3) 软删不触发级联是事实（数据库里孤儿关系行仍在），断言这一点让因果链可见
4) 新增可见收藏后计数恢复正常（修复没有把正常路径搞坏）
"""
from _verify_common import (
    api,
    check,
    cleanup_project,
    create_project,
    finish,
    register,
    sql_one,
)


def chk(label, cond, actual=""):
    check(f"{label}（实际 {actual}）" if actual != "" else label, cond)


def favorites(token):
    return api("/users/me/favorites", token=token)["data"]


def favorite_count(token):
    return api("/users/me/stats", token=token)["data"]["favoriteCount"]


def orphan_rows(uid):
    """该用户的收藏关系行数（不看项目是否已软删）——用来证明级联没触发"""
    return int(sql_one(f"SELECT COUNT(*) FROM project_favorites WHERE user_id={uid}") or 0)


def visible_rows(uid):
    """该用户仍可见的收藏关系行数（排除软删项目）"""
    return int(
        sql_one(
            "SELECT COUNT(*) FROM project_favorites f "
            "JOIN projects p ON p.id = f.project_id "
            f"WHERE f.user_id={uid} AND p.deleted_at IS NULL"
        )
        or 0
    )


def main():
    a, b = register("favsda"), register("favsdb")
    print("用户", a["uid"], b["uid"])

    p1 = create_project(a["token"], f"软删收藏验证项目 {a['username']}")
    p2 = None

    try:
        # ---------- 1) 正常路径 ----------
        api(f"/projects/{p1}/favorite", {}, token=b["token"])
        d = favorites(b["token"])
        chk("正常：收藏 1 个未删项目，total=1", d["total"] == 1, d["total"])
        chk("正常：列表条数=1", len(d["projects"]) == 1, len(d["projects"]))
        chk("正常：favoriteCount=1", favorite_count(b["token"]) == 1, favorite_count(b["token"]))

        # ---------- 2) 软删该项目 ----------
        api(f"/projects/{p1}", token=a["token"], method="DELETE")

        # 先钉住「软删不触发级联」这个事实：关系行还在，项目已不可见
        chk("软删后收藏关系行仍留在表里（级联未触发）", orphan_rows(b["uid"]) == 1, orphan_rows(b["uid"]))
        chk("软删后仍可见的收藏为 0", visible_rows(b["uid"]) == 0, visible_rows(b["uid"]))

        d = favorites(b["token"])
        chk("软删后列表条数=0", len(d["projects"]) == 0, len(d["projects"]))
        chk("软删后 total 与条数一致（都为 0）", d["total"] == len(d["projects"]), f"total={d['total']} len={len(d['projects'])}")
        chk("软删后 favoriteCount 不再虚高", favorite_count(b["token"]) == 0, favorite_count(b["token"]))

        # 分页边界：total 若虚高，第二页会去取一个不存在的区间
        d2 = api("/users/me/favorites?page=2&pageSize=10", token=b["token"])["data"]
        chk("软删后第二页也为空", len(d2["projects"]) == 0 and d2["total"] == 0, f"total={d2['total']} len={len(d2['projects'])}")

        # ---------- 3) 修复不能把正常路径搞坏 ----------
        p2 = create_project(a["token"], f"软删收藏正常路径 {a['username']}")
        api(f"/projects/{p2}/favorite", {}, token=b["token"])
        d = favorites(b["token"])
        chk("新增可见收藏后 total=1", d["total"] == 1, d["total"])
        chk("新增可见收藏后条数=1", len(d["projects"]) == 1, len(d["projects"]))
        chk("新增可见收藏后 favoriteCount=1", favorite_count(b["token"]) == 1, favorite_count(b["token"]))
        chk("列表里那条就是新项目", d["projects"][0]["id"] == p2, d["projects"][0]["id"] if d["projects"] else None)

    finally:
        cleanup_project(p1, (a["uid"], b["uid"]))
        if p2:
            cleanup_project(p2)

    finish()


if __name__ == "__main__":
    main()
