# -*- coding: utf-8 -*-
"""加密共创项目验证

覆盖：
- 仓库加密：内容公开、仓库地址隐藏；错误密码 403、正确密码拿到地址
- 整项目加密：介绍 / 标签 / 仓库 / 共创伙伴全部隐藏；错误密码 403、正确密码拿到完整详情
- 配额：每个账号最多 1 个加密项目（第二个 409），公开项目不受影响；
  取消加密后槽位释放，可以重新创建
- 侧信道：整项目加密的项目不能被标签筛选 / 介绍关键词搜索命中，相关推荐为空
- 落库：密码只存 bcrypt 哈希、lock_slot_user_id 指向发起人
运行：
    "C:\\Users\\28916\\AppData\\Local\\Programs\\Python\\Python313\\python.exe" scripts/verify_encrypted_project.py
"""
from urllib.parse import quote

from _verify_common import (
    api,
    api_status,
    check,
    cleanup_project,
    cleanup_users,
    finish,
    register,
    sql_one,
)

REPO_URL = "https://github.com/example/encrypted-project"
LOCK_PASSWORD = "unlock-me-2026"
NEW_PASSWORD = "unlock-me-2027"


def description(secret):
    return f"这是一条用于加密项目验证的临时介绍，写长一点以便通过 20 字下限，并包含秘密词{secret}。"


def build_body(title_suffix, secret=None, **kw):
    return {
        "title": f"加密验证{title_suffix}",
        "description": description(secret or title_suffix),
        "categoryId": 1,
        **kw,
    }


def main():
    pids = []
    uids = []
    try:
        owner = register("encrepo")
        other = register("encproj")
        uids += [owner["uid"], other["uid"]]
        token = owner["token"]
        other_token = other["token"]
        secret_word = "秘密词" + owner["username"]
        secret_tag = "秘标" + owner["username"][:8]

        # ---------- 仓库加密 ----------
        p_repo = api(
            "/projects",
            build_body("仓库", repositoryUrl=REPO_URL, lockLevel="repo", lockPassword=LOCK_PASSWORD),
            token=token,
        )["data"]
        pids.append(p_repo["id"])
        check("创建仓库加密项目成功", p_repo["lockLevel"] == "repo")

        anon = api(f"/projects/{p_repo['id']}")["data"]
        check("仓库加密：游客仍能看到项目介绍", anon["description"] != "")
        check("仓库加密：游客看不到仓库地址", anon["repositoryUrl"] is None)
        check("仓库加密：游客拿到 repoLocked 标记", anon["repoLocked"] is True and anon["locked"] is False)

        viewer = api(f"/projects/{p_repo['id']}", token=other_token)["data"]
        check("仓库加密：其他登录用户同样看不到仓库地址", viewer["repositoryUrl"] is None and viewer["repoLocked"] is True)

        status, body = api_status(
            f"/projects/{p_repo['id']}/unlock", {"password": "wrong-password"}, method="POST"
        )
        check("仓库加密：错误密码返回 403", status == 403)
        check("错误密码给出可读提示", body.get("message") == "密码不正确，请重试")

        unlocked = api(
            f"/projects/{p_repo['id']}/unlock", {"password": LOCK_PASSWORD}, method="POST"
        )["data"]
        check("仓库加密：正确密码返回仓库地址", unlocked["repositoryUrl"] == REPO_URL)
        check("解锁响应标记 unlocked", unlocked["unlocked"] is True and unlocked["lockLevel"] == "repo")

        owner_view = api(f"/projects/{p_repo['id']}", token=token)["data"]
        check("发起人免密看到完整仓库地址", owner_view["repositoryUrl"] == REPO_URL and owner_view["repoLocked"] is False)

        status, _ = api_status(f"/projects/{p_repo['id']}/unlock", {}, token=token, method="POST")
        check("发起人调解锁接口免密通过", status == 200)

        # 仓库加密但没有仓库地址：拒绝创建，避免「锁住空气」
        status, body = api_status(
            "/projects",
            build_body("无仓库", lockLevel="repo", lockPassword=LOCK_PASSWORD),
            token=other_token,
        )
        check("仓库加密缺仓库地址返回 400", status == 400 and "仓库地址" in body.get("message", ""))

        # 密码长度下限
        status, body = api_status(
            "/projects",
            build_body("短密码", lockLevel="project", lockPassword="123"),
            token=other_token,
        )
        check("加密密码过短返回 400", status == 400 and "6" in body.get("message", ""))

        # ---------- 配额：每个账号最多 1 个加密项目 ----------
        status, body = api_status(
            "/projects",
            build_body("第二个", lockLevel="project", lockPassword=LOCK_PASSWORD),
            token=token,
        )
        check("同一账号第二个加密项目返回 409", status == 409)
        check("配额提示可读", "1 个加密项目" in body.get("message", ""))

        # 公开项目不受配额影响
        p_public = api("/projects", build_body("公开"), token=token)["data"]
        pids.append(p_public["id"])
        check("同一账号仍可创建公开项目", p_public["lockLevel"] == "none")

        quota = api("/projects/encryption-status", token=token)["data"]
        check(
            "加密配额状态指向已创建的加密项目",
            quota["hasEncryptedProject"] is True and quota["project"]["id"] == p_repo["id"],
        )

        # ---------- 整项目加密 ----------
        p_project = api(
            "/projects",
            build_body(
                "整项目",
                secret=secret_word,
                repositoryUrl=REPO_URL,
                tags=[secret_tag],
                lockLevel="project",
                lockPassword=LOCK_PASSWORD,
            ),
            token=other_token,
        )["data"]
        pids.append(p_project["id"])
        check("创建整项目加密成功", p_project["lockLevel"] == "project")

        locked = api(f"/projects/{p_project['id']}")["data"]
        check("整项目加密：介绍不下发", locked["description"] == "")
        check("整项目加密：标签不下发", locked["tags"] == [])
        check("整项目加密：仓库地址不下发", locked["repositoryUrl"] is None)
        check("整项目加密：共创伙伴不下发", locked["participants"] == [])
        check("整项目加密：locked 标记为真", locked["locked"] is True and locked["repoLocked"] is True)
        check("整项目加密：标题仍然可见", locked["title"].startswith("加密验证整项目"))

        status, _ = api_status(
            f"/projects/{p_project['id']}/unlock", {"password": "wrong-password"}, method="POST"
        )
        check("整项目加密：错误密码返回 403", status == 403)

        full = api(
            f"/projects/{p_project['id']}/unlock", {"password": LOCK_PASSWORD}, method="POST"
        )["data"]
        check("整项目加密：正确密码返回完整项目", full["project"]["description"] == description(secret_word))
        check("整项目加密：解锁后标签回来", full["project"]["tags"] == [secret_tag])
        check("整项目加密：解锁后仓库地址回来", full["project"]["repositoryUrl"] == REPO_URL)
        check("整项目加密：解锁后共创伙伴回来", len(full["project"]["participants"]) >= 1)
        check("解锁后不再标记 locked", full["project"]["locked"] is False)

        # ---------- 侧信道 ----------
        search_ids = [
            p["id"]
            for p in api(f"/projects?search={quote(secret_word)}&pageSize=50")["data"]["projects"]
        ]
        check("整项目加密的介绍关键词搜不到该项目", p_project["id"] not in search_ids)

        tag_ids = [
            p["id"]
            for p in api(f"/projects?tag={quote(secret_tag)}&pageSize=50")["data"]["projects"]
        ]
        check("整项目加密的标签筛选命中不到该项目", tag_ids == [])

        check("整项目加密的相关推荐为空", api(f"/projects/{p_project['id']}/related")["data"] == [])

        rows = api(f"/projects?creatorId={other['uid']}&pageSize=50")["data"]["projects"]
        row = next((p for p in rows if p["id"] == p_project["id"]), None)
        check("广场列表仍展示加密项目（标题可见）", row is not None and row["title"].startswith("加密验证整项目"))
        check("广场列表不带仓库地址", row is not None and row["repositoryUrl"] is None)
        check("广场列表带 locked / lockLevel 标记", row is not None and row["locked"] is True and row["lockLevel"] == "project")

        # ---------- 落库 ----------
        raw_hash = sql_one(f"SELECT lock_password_hash FROM projects WHERE id = {p_repo['id']}")
        check("密码以 bcrypt 哈希落库（不是明文）", raw_hash.startswith("$2") and LOCK_PASSWORD not in raw_hash)
        slot = sql_one(f"SELECT lock_slot_user_id FROM projects WHERE id = {p_repo['id']}")
        check("加密槽位指向发起人", slot == str(owner["uid"]))
        check(
            "公开项目不占加密槽位",
            sql_one(f"SELECT COALESCE(lock_slot_user_id,'') FROM projects WHERE id = {p_public['id']}") == "",
        )

        # ---------- 改密码 / 取消加密 / 槽位释放 ----------
        status, _ = api_status(
            f"/projects/{p_repo['id']}", {"lockLevel": "repo", "lockPassword": NEW_PASSWORD}, token=token, method="PUT"
        )
        check("编辑加密项目改密码成功", status == 200)

        status, _ = api_status(
            f"/projects/{p_repo['id']}/unlock", {"password": LOCK_PASSWORD}, method="POST"
        )
        check("改密后旧密码失效", status == 403)

        new_unlocked = api(
            f"/projects/{p_repo['id']}/unlock", {"password": NEW_PASSWORD}, method="POST"
        )["data"]
        check("新密码可以解锁", new_unlocked["repositoryUrl"] == REPO_URL)

        status, body = api_status(f"/projects/{p_repo['id']}", {"lockLevel": "none"}, token=token, method="PUT")
        check("取消加密成功", status == 200 and body["data"]["lockLevel"] == "none")
        check(
            "取消加密后槽位已释放",
            sql_one(f"SELECT COALESCE(lock_slot_user_id,'') FROM projects WHERE id = {p_repo['id']}") == "",
        )

        status, _ = api_status(
            f"/projects/{p_repo['id']}/unlock", {"password": NEW_PASSWORD}, method="POST"
        )
        check("取消加密后解锁接口返回 400", status == 400)
        check("取消加密后配额状态恢复", api("/projects/encryption-status", token=token)["data"]["hasEncryptedProject"] is False)

        p_again = api(
            "/projects",
            build_body("重新加密", repositoryUrl=REPO_URL, lockLevel="repo", lockPassword=LOCK_PASSWORD),
            token=token,
        )["data"]
        pids.append(p_again["id"])
        check("槽位释放后可以重新创建加密项目", p_again["lockLevel"] == "repo")
        check(
            "重新创建的加密项目占回槽位",
            sql_one(f"SELECT lock_slot_user_id FROM projects WHERE id = {p_again['id']}") == str(owner["uid"]),
        )

    finally:
        for pid in pids:
            try:
                cleanup_project(pid)
            except Exception as err:  # noqa: BLE001 - 清理失败不该盖住本轮结论
                print(f"cleanup project {pid} failed: {err}")
        cleanup_users(uids)


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:  # noqa: BLE001 - 崩溃也要走到汇总
        import traceback

        traceback.print_exc()
        from _verify_common import crash

        crash(exc)
    finally:
        finish()
