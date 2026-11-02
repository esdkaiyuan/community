# -*- coding: utf-8 -*-
"""邮箱验证接入的本地可执行断言（不依赖外部邮件服务）。

这里只钉「输入收口」与「历史登录兼容」：
  · 非法邮箱 / 缺字段 / 非法验证码 / 弱密码在调用外部服务之前就被 400 挡下
  · 历史账号密码登录仍然可用（本地镜像先比一次）
  · 401 仍然是 401（外部服务重启 / 限流不该把登录失败改成 503）
  · 响应里绝不出现外部 API Key 的 `sk-` 前缀

真正的「发信 → 收码 → 验证」需要真实邮箱，由人工联调覆盖；CI 里不依赖外部邮件。
"""
from _verify_common import api_status, check, cleanup_users, finish, register, PASSWORD

UIDS = []


def main():
    user = register("mailauth")
    UIDS.append(user["uid"])
    email = f"{user['username']}@example.com"
    print("临时用户:", user["uid"], email)

    # 1. 历史账号密码登录：本地镜像先比，且不能因为外部服务不可用而变 503
    status, body = api_status("/users/login", {"email": email, "password": PASSWORD})
    check("历史账号密码登录仍可用", status == 200 and bool(body.get("data", {}).get("token")))

    status, body = api_status("/users/login", {"email": email, "password": "wrong-password"})
    check("密码错误仍是 401（不是 503）", status == 401)
    check("密码错误文案不区分邮箱是否存在", "邮箱或密码错误" in body.get("message", ""))

    # 2. 发验证码：邮箱格式在本地就收口，不消耗外部额度
    status, body = api_status("/users/email/send-code", {"email": "bad-email"})
    check("非法邮箱发码 → 400", status == 400)
    check("非法邮箱文案是中文人话", "邮箱格式不正确" in body.get("message", ""))

    status, _ = api_status("/users/email/send-code", {})
    check("缺邮箱发码 → 400", status == 400)

    # 3. 验证码登录：格式错误在本地挡下，不请求外部
    status, body = api_status("/users/login/email", {"email": email, "code": "abc"})
    check("非法验证码格式登录 → 400", status == 400)
    check("非法验证码文案说明是 6 位", "6 位" in body.get("message", ""))

    status, _ = api_status("/users/login/email", {"email": email})
    check("缺验证码登录 → 400", status == 400)

    status, _ = api_status("/users/login/email", {"email": "bad-email", "code": "123456"})
    check("非法邮箱验证码登录 → 400", status == 400)

    # 4. 验证码注册：所有本地校验都先于外部调用
    status, _ = api_status(
        "/users/register/email",
        {"username": "x", "email": email, "password": PASSWORD, "code": "123456"},
    )
    check("用户名过短注册 → 400", status == 400)

    status, _ = api_status(
        "/users/register/email",
        {"username": "mailreg", "email": "bad-email", "password": PASSWORD, "code": "123456"},
    )
    check("非法邮箱注册 → 400", status == 400)

    status, _ = api_status(
        "/users/register/email",
        {"username": "mailreg", "email": email, "password": "123", "code": "123456"},
    )
    check("弱密码注册 → 400", status == 400)

    status, _ = api_status(
        "/users/register/email",
        {"username": "mailreg", "email": email, "password": PASSWORD, "code": "abc"},
    )
    check("非法验证码注册 → 400", status == 400)

    status, _ = api_status(
        "/users/register/email",
        {"username": "mailreg", "email": email, "password": PASSWORD},
    )
    check("缺验证码注册 → 400", status == 400)

    # 5. 找回密码：两次密码不一致 / 非法验证码都在本地挡下
    status, body = api_status(
        "/users/password/reset",
        {"email": email, "code": "123456", "password": PASSWORD, "confirmPassword": "other-pass"},
    )
    check("两次新密码不一致 → 400", status == 400)
    check("密码不一致文案是中文人话", "两次输入的密码不一致" in body.get("message", ""))

    status, _ = api_status(
        "/users/password/reset",
        {"email": email, "code": "abc", "password": PASSWORD, "confirmPassword": PASSWORD},
    )
    check("非法验证码重置密码 → 400", status == 400)

    status, _ = api_status(
        "/users/password/reset",
        {"email": "bad-email", "code": "123456", "password": PASSWORD, "confirmPassword": PASSWORD},
    )
    check("非法邮箱重置密码 → 400", status == 400)

    # 6. 响应里不允许出现外部 Key 的前缀
    _, body = api_status("/users/login/email", {"email": email, "code": "abc"})
    check("响应不泄露外部 API Key", "sk-" not in str(body))

    # 7. 新入口不能是 404（路由确实挂上了）
    for path, payload in [
        ("/users/email/send-code", {"email": "bad-email"}),
        ("/users/login/email", {"email": email, "code": "abc"}),
        ("/users/register/email", {}),
        ("/users/password/reset", {}),
    ]:
        status, _ = api_status(path, payload)
        check(f"{path} 已挂载（不是 404）", status != 404)


if __name__ == "__main__":
    try:
        main()
    finally:
        cleanup_users(UIDS)
        print("已清理临时用户")
    finish()