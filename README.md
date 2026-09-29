# 共创社区平台 - 启动指南

## 前置要求

1. **Node.js** (v16+)
2. **MySQL** (v8.0+)
3. **npm** 或 **yarn**

## 快速开始

### 1. 配置数据库

#### 创建数据库
在 MySQL 中执行以下命令：

```sql
CREATE DATABASE community_platform CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

#### 修改数据库配置
编辑 `backend/.env` 文件，修改数据库密码：

```env
DB_PASSWORD=你的MySQL密码
```

### 2. 初始化数据库

在 MySQL 中执行数据库脚本：

```bash
mysql -u root -p community_platform < backend/database/schema.sql
mysql -u root -p community_platform < backend/database/seed.sql
```

或者手动执行 SQL 文件中的内容。

### 3. 安装依赖

```bash
# 后端
cd backend
npm install

# 前端
cd frontend
npm install
```

### 4. 启动服务

#### 启动后端（终端 1）
```bash
cd backend
npm run dev
```

后端服务将运行在 http://localhost:5000

#### 启动前端（终端 2）
```bash
cd frontend
npm run dev
```

前端服务将运行在 http://localhost:3001

### 5. 访问应用

打开浏览器访问 http://localhost:3001

## 功能说明

### 已完成的功能

✅ **前端功能**
- [x] 首页 - 项目列表展示（卡片形式）
- [x] 顶部导航栏 - Logo、搜索框、登录/注册、消息通知入口
- [x] 左侧边栏 - 分类筛选
- [x] 项目卡片 - 封面、标题、描述、参与人数、点赞数、就地收藏
- [x] 登录/注册页面
- [x] 发布 / 编辑项目页面（含封面图片上传：点击或拖拽，支持外链兜底）
- [x] 项目详情页面（含评论与回复、点赞、参与、浏览次数与发布日期规格条）
- [x] 公开主页 - 「TA 发布的 / TA 参与的」，可下钻到广场筛选视图
- [x] 搜索、标签筛选、排序（最新 / 最热 / 本周活跃）
- [x] 通知中心（含深链直达某条评论）
- [x] 响应式布局 + 深浅色主题
- [x] 统一错误提示与表单内联校验

✅ **后端功能**
- [x] 用户认证（JWT）
- [x] 用户注册/登录
- [x] 项目 CRUD（含封面 URL 持久化）
- [x] 封面图片上传（类型/体积/魔数三重校验 + 静态直出）
- [x] 分类列表
- [x] 点赞 / 收藏 / 参与功能
- [x] 评论与回复
- [x] 站内通知（参与 / 评论 / 点赞 / 收藏 / 回复）
- [x] 标签归一化与相关推荐
- [x] 操作日志（发布 / 编辑 / 删除项目、发表 / 删除评论、注册 / 改资料全量留痕，写入前统一净化）
- [x] 用户资料字段归一化（用户名 / 简介剥 emoji 与控制字符，注册与改名共用一个口径）
- [x] 安全事件（登录失败 / 注册被拒 / 令牌无效留痕，账号脱敏 + 按来源聚合，绝不记密码）

### 待完善的功能

⏳ **需要进一步完善**
- [ ] 图片裁剪 / 压缩（当前只做体积上限校验）
- [ ] 自动化测试接入 CI（`scripts/` 下的验证脚本目前靠手动执行）
- [ ] 单元测试

## 上传文件的清理策略

封面上传会产生磁盘文件，本项目用「实时回收 + 定期清扫」两层兜住，不会无限堆积：

1. **实时回收**：编辑项目时更换封面、清空封面、把封面换成站外链接，旧的站内文件会在保存成功后立即删除。
   删除前会再查一次引用数 —— 同一张图被多个项目引用时不会误删（`backend/src/services/cover.service.js`）。
2. **定期清扫**：兜住「选了图、图已落盘、但用户没提交就关页面」这类服务端无从归属的文件。

```bash
cd backend
npm run uploads:prune:dry   # 干跑：只列出孤儿候选，不删任何东西
npm run uploads:prune       # 真删（等价于 node scripts/prune-uploads.js --apply）
```

判定「孤儿」需要同时满足三条，口径刻意保守：文件位于 `backend/uploads/projects/` 且命名符合服务端规则、
**全表（含软删除项目）没有任何 `cover_image` 指向它**、且修改时间已超过宽限期（默认 24 小时）。
宽限期是为了避开竞态：正在填表单的人，他的图还没被任何项目引用，但那不是垃圾。

生产环境已在 `backend/ecosystem.config.js` 里注册了一个 PM2 定时任务，每天凌晨 3:30 自动执行清扫，
不需要额外配置 crontab。

## 操作日志（审计留痕）

凡是「用户产生内容」的写操作都会自动落一条日志，存到数据库表 `activity_logs`：

| 动作 | 触发点 |
| --- | --- |
| `project.create` | 发布项目 |
| `project.update` | 编辑项目（**只记真正改动的字段**，空 PUT 不产生日志） |
| `project.delete` | 删除项目 |
| `comment.create` | 发表评论 / 回复（`detail.isReply` 区分） |
| `comment.delete` | 删除评论 |
| `user.register` | 注册账号（审计时间线的起点，之后所有日志靠 `user_id` 串起来） |
| `user.profile.update` | 修改个人资料；**改名会记下旧值 → 新值**（见下） |

每条日志记下：操作者（id + **名称快照**）、动作、目标、所属项目、一行摘要、结构化附加、来源 IP、UA、时间。

**有意不记的动作**：点赞 / 取消点赞、收藏 / 取消收藏、参与 / 退出、通知已读。它们是高频、可反复
切换、且不产生内容的操作 —— 记进来只会把日志淹没（刷一次首页就能造出几十行），取证价值接近零。
审计日志的标准是「每条都值得人读一遍」。真要做异常行为检测，应该另起一张行为流水表 + 聚合，
而不是往审计日志里灌明细。

**为什么改名要专门记旧值 → 新值**：`activity_logs.username` 是**快照**，用户改名后此前所有日志行
里仍是旧名字（这是刻意的，快照就该反映「他动手时叫什么」）。但如果没有一条记录写下「旧的叫 A、
新的叫 B」，事后就再也解释不清「同一个 `user_id` 为什么有两个名字」。所以
`user.profile.update` 的 `detail` 里带 `usernameFrom` / `usernameTo`。
`bio` / `avatar` 只记「改没改」（`detail.changed`），不存值 —— 日志是留痕，不是内容备份。
另外这个动作**不记 email**：审计只需 `user_id` 就能把同一个人的行为串起来，而日志留存 365 天，
多存一份邮箱等于平白扩大 PII 面。

**为什么日志表刻意不建外键**：本仓库的删除链路是 `users → projects → project_comments` 一路
`ON DELETE CASCADE`。日志是证据，必须比它描述的对象活得久 —— 一旦挂上外键，注销一个账号就会把
证据链一起抹掉，而那恰恰是最需要留痕的场景。所以只存 id + 名称快照。代价是可能出现「孤儿日志」，
这对审计来说是特性不是缺陷。推论：**清理测试数据时必须显式删 `activity_logs`**，级联收拾不了它。

### 防注入规则

用户能写进标题和评论的任何字符，最终都会进日志表。所以写入前统一走
`backend/src/utils/logSanitize.js`，四类注入面一次性处理：

1. **日志伪造（CRLF 注入）**：正文里塞 `\r\n[ERROR] …` 就能在下游日志系统里凭空多出一条记录。
   `\r` `\n` `U+2028` `U+2029` 一律压成空格 → 每条摘要永远是单行。
2. **控制字符与终端转义**：ANSI CSI 序列（`\x1b[31m`）整体摘除，`\x00`–`\x1f` / `\x7f`–`\x9f` 全部移除。
3. **Unicode 方向控制**：`U+202E`（RLO）能让文本反向显示、零宽字符能在看不见处粘连文本，一并移除。
4. **存储放大**：单条用户内容最多留 **60 字**预览，超长截断并在末尾加 `…`（不静默丢弃）；
   摘要整体上限 255 字。日志是留痕，不是内容备份。

另外三条结构性约束，都在服务层（`backend/src/services/activityLog.service.js`）强制：

- **动作白名单**：只认上表五个动作，未知 `action` 直接拒绝（不静默入库）。
- **detail 键白名单**：`sanitizeDetail` 是「按白名单取键」而不是「遍历传入对象」，
  所以任意键（含 `__proto__` 这类原型污染载荷）天然进不来；嵌套对象一律丢弃。
- **失败不外抛**：日志写失败只打 error 日志，绝不让用户的发布 / 评论失败。

前端渲染约定：**日志只做纯文本渲染，禁止 `v-html`**。这是刻意不剥离 `<` `>` 的原因 ——
共创社区里用户真的会讨论标签写法，改写成 `&lt;` 既让审计失真又会被二次转义。

### 身份字段：用户名与简介的归一化

日志的九个可写列里，八个都过了 `sanitize*`，唯独 `username` 走的是「从库里读出来直接落库」——
而它恰好是唯一由用户直接控制的身份字段。实测注册用户名 `"a\r\nFAKE"`（长度 7，落在 2~20 的
校验区间内）能一路通过，`activity_logs.username` 里真的躺进了 CRLF（HEX `610D0A46414B45`），
下游按行解析的日志系统会由此凭空多出一条伪造记录 —— **整条净化链被这一个字段绕开了**。

修法是两层，缺一不可：

1. **输入侧归一化**（`user.service.js` 的 `normalizeUsername` / `normalizeBio`，注册与改名共用
   同一个函数）：剥 emoji（全站约定，此前只覆盖了评论 / 标题 / 标签，漏了用户名与简介）→
   去掉 C0/C1 控制字符与零宽 / 方向控制 → 折叠空白 → 收边。简介是多行文本，**保留换行**，
   只统一 CRLF。剥完不足 2 字的用户名直接 400，不静默截断成短名。
   净化一旦改动了内容，响应会返回 `adjusted: true` 并在 message 里说明 —— 不做静默修改。
2. **日志侧收口**（`activityLog.service.js` 的 `resolveUsername`）：回查出来的用户名同样过
   `sanitizeLogText`。**日志列的完整性不能依赖「上游字段干净」** —— 否则将来任何一个新字段
   忘了洗，同一个洞会再开一次。

前端在提交时也剥一遍 emoji（与 `ProjectForm` 同一约定），目的是让改动在表单里**可见**，
服务端才是契约。控制字符不需要前端处理：`<input>` 里本来就打不出换行。

控制字符与零宽字符的正则只允许出现在 `utils/textSanitize.js` 与 `utils/logSanitize.js` 两个
模块 —— 这类正则天然会触发 eslint 的 `no-control-regex`（规则方向在这里是反的），集中豁免并
写明理由，好过让每个调用方各挂一次看不懂的豁免。

### 读取与留存

```bash
# 只查自己的操作记录（不接受任何 userId 参数；本项目暂无角色体系，不提供看他人日志的接口）
GET /api/logs/me?page=1&pageSize=20&action=comment.create&projectId=12
```

日志只写不删，是唯一会无限增长的业务表，所以配了留存期清理：

```bash
cd backend
npm run logs:prune:dry   # 干跑：只报告超出留存期的条数与动作分布
npm run logs:prune       # 真删（等价于 node scripts/prune-activity-logs.js --apply）
```

留存期默认 365 天，可用 `--days=N` 覆盖，**两张日志表一起清**。生产环境已在
`ecosystem.config.js` 注册 PM2 定时任务，每天凌晨 4:00 执行。

### 验证

```bash
cd backend && npm run logs:check          # 净化规则的纯函数自检（59 项）
python scripts/verify_activity_logs.py    # 端到端：真实注入载荷落库后逐条断言（108 项）
```

`verify_activity_logs.py` 里有两段值得单独说：

- **K 段绕开服务层直接改库**，把 `users.username` 改成 `UNHEX('610D0A46414B45')`，再触发一次写
  日志 —— 验的是「日志列的完整性不依赖上游字段干净」这条防御纵深本身。正常路径下脏用户名已经
  进不了库，只靠接口测是测不到这一层的。
- **响应字段一律用 `.get()` 取**：旧实现里字段不存在时那一条**变红**，而不是 `KeyError` 把后面
  的断言全跳过。本轮修复前跑一遍得到 **74 OK / 34 FAIL**，修后 **108 OK / 0 FAIL**。

## 安全事件（被拒的尝试）

审计日志只覆盖**做成了什么**。可攻击者留下的痕迹恰恰全在**没做成**的那一侧：撞库、账号枚举、
伪造令牌。这类事件存在表 `security_events`，与 `activity_logs` **刻意分成两张表**：

| | `activity_logs` | `security_events` |
| --- | --- | --- |
| 记什么 | 谁**做成了**什么 | 有人**尝试但没成功** |
| 身份 | 一定有（`user_id`） | 大多没有（未登录 / 密码错 / 令牌伪造） |
| 那一列的语义 | 操作者 | **被瞄准的账号**（`target_user_id`） |
| 谁能读 | 用户自己（`/logs/me`） | 只看针对自己账号的（`/logs/me/security`） |
| 一行代表 | 一次操作 | 「同一来源在窗口内对同一目标失败了 N 次」 |

| 事件 | 触发点 | 记下什么 |
| --- | --- | --- |
| `auth.login.rejected` | 登录失败（密码错 / 账号不存在） | 被瞄准的账号（若确实存在）、脱敏账号、IP、UA、来源接口 |
| `auth.register.rejected` | 注册被拒（校验不过 / 撞名 / 撞邮箱） | 尝试的用户名（脱敏）、撞上的账号（若撞名） |
| `auth.token.rejected` | 带了 token 却验不过（签名 / 格式错） | 被打的接口 + 来源 |

**为什么不记密码、账号还要脱敏**：日志留存 365 天，密码（任何形态：明文 / 长度 / 哈希）进一次库
就是一笔永久的负债；账号也只留脱敏形态（`z***@e***.com` / `a***`）。写入是**按白名单字段显式取值**，
不是遍历传入的对象 —— 调用方多传 `password` / `body` 也进不来，
`backend/scripts/check-security-log.js` 里有专门钉这件事的断言。

**为什么必须聚合**：暴力破解的本质就是「同一来源对同一目标反复失败」。一条一次会瞬间把表刷成噪音
洪水，真正有信息量的「第一次」反而被淹掉。所以按 `sha256(event|ip|account|targetUserId|path)` 聚合，
窗口（10 分钟）内重复只把 `occurrences + 1` 并刷新 `last_seen_at` —— 读出来是「这个 IP 在 10 分钟里
对 `z***@e***.com` 试了 47 次」。`targetUserId` **必须**在键里：脱敏一定会碰撞
（`secA…@example.com` 与 `secB…@example.com` 都变成 `s***@e***.com`），少了它两个账号会被并成一行，
而且行里的 `target_user_id` 会被覆盖成后一个，**日志会指错人** —— 比没记更糟。这是实测抓到的真 bug。

**哪些不记（同等重要）**：没带 token（未登录，正常）、token 过期（会话到期，正常）、
`optionalAuth` 的静默退化（公开页面上一个旧 token 会让每次浏览都触发一次）。记了就是日志洪水 ——
所以判据是「签名 / 格式对不上」才记，用 jsonwebtoken 的**错误类型**判断，不要 match message 文本。

**为什么留痕只 await 不抛**：写日志失败绝不能把本该是 401 的响应变成 500，更不能把请求挂住
（本仓库是 Express 4，async 中间件的 reject **不会**自动交给 errorHandler）——
`middleware/auth.js` 为此单独套了一层 try/catch。

### 读取与留存

```bash
# 只看针对自己账号的被拒尝试（同样不接受任何 userId 参数）
GET /api/logs/me/security?page=1&pageSize=20&event=auth.login.rejected
```

`npm run logs:prune*` 会**同时**清 `activity_logs` 与 `security_events`：两张表的留存策略本来就是
同一个，分成两个脚本早晚会漏掉一个。

### 验证

```bash
cd backend && npm run security:check         # 白名单 / 脱敏 / 聚合键 / 绝不记密码（纯函数，59 项）
python scripts/verify_security_events.py     # 端到端：真实失败尝试落库后逐条断言（89 项）
```

两条最有价值的断言：**5 个并发失败尝试一次都没丢**（`occurrences` 必须是 SQL 层原子自增，而不是
「读出来 +1 再写回」），以及**「缺 token / 过期 token / optionalAuth 一次都没写」**——
负向断言和正向同等重要，它们是挡住日志洪水的那道闸。

## 接口健壮性（横向巡检）

所有接口共用一套「用户可控输入」的收口规则，并有一个脚本横向体检。

### 分页与取数上限

凡是要进 SQL `LIMIT` / `OFFSET` 的数字（`page` / `pageSize` / `limit`）都走
`backend/src/utils/pagination.js` 的 `clampInt`，**上界只在这一处定义**：

```js
const limit = clampInt(pageSize, { max: 50, fallback: 12 })
page = clampInt(page, { max: MAX_PAGE, fallback: 1 })
```

为什么必须收口：`?page=99999999999999999999` 会让 `(page - 1) * limit` 越过
`Number.MAX_SAFE_INTEGER`，被序列化成 `1.2e+22` 这种科学计数法拼进 SQL，数据库报语法错 →
用户收到 500。收口之前这行代码在 6 个 service 里各写了一遍，**8 处全都漏了 `page` 的上界**。

### 排序参数只认自有键

`?sort=` 只允许命中白名单里的键：

```js
// ❌ SORT_MAP[sort]：?sort=__proto__ 会命中原型链上的 Object.prototype，
//    它是 truthy，绕过了 `|| 默认值` 的兜底，塞给 Sequelize 直接 500
// ✅ 用 hasOwnProperty 收口到自有键，坏值一律退回默认排序
const sortOrder = Object.prototype.hasOwnProperty.call(SORT_MAP, sort) ? SORT_MAP[sort] : SORT_MAP.latest
```

### 横向巡检

```bash
python scripts/audit_backend_api.py
```

「坏输入 × 全端点」矩阵（约 970 项断言），与 `scripts/audit_frontend_ui.py` 互补：
前端巡检管「页面长得对不对」，它管「接口在坏输入下会不会把 500 甩给用户」。五条不变量：

1. 任何**用户可控输入**都不得产生 5xx —— 能预见的坏输入必须是 4xx；
2. 所有响应恒为 `{code, message, data?}`，且 `code === HTTP 状态码`；
3. 所有 4xx 的 `message` 必须是中文人话，不含英文技术原文；
4. 受保护端点无 token / 坏 token 一律 401（不是 500，也不是 200）；
5. 方法不匹配 / 路由不存在一律 404（不是 500）。

⚠️ 请求量较大，**请单独跑**，不要与其它验证脚本并跑 —— 否则会撞全局限流（600 次 / 15 分钟）把结果染红。
撞了重启后端即可清零（`express-rate-limit` 用内存计数）。

## 常见问题

### 1. 后端启动失败

**问题**: `Error: Cannot find module '../../config/database'`

**解决**: 确保所有模型文件的引用路径正确，应该是 `require('../config/database')`

### 2. 数据库连接失败

**问题**: `Access denied for user 'root'@'localhost'`

**解决**: 检查 `backend/.env` 文件中的数据库用户名和密码是否正确

### 3. 前端 API 请求失败

**问题**: `Network Error` 或 `500 Internal Server Error`

**解决**: 
- 确保后端服务已启动
- 确保数据库已创建并初始化
- 检查 `frontend/vite.config.js` 中的代理配置

### 4. 端口被占用

**问题**: `Port 3001 is already in use`

**解决**: 
- 修改 `frontend/vite.config.js` 中的 `server.port`
- 或者关闭占用端口的进程

> 注意：Vite 默认监听 `localhost`（本机可能解析到 IPv6 的 `::1`）。用 `127.0.0.1:3001` 访问可能连不上，请用 `localhost:3001`。

## 技术栈

### 前端
- Vue 3 (Composition API + `<script setup>`)
- Vite
- Tailwind CSS 4（设计令牌走 CSS 变量，深浅色自动翻转）
- Pinia
- Vue Router 4
- Axios

### 后端
- Node.js
- Express 4
- MySQL 8
- Sequelize
- JWT
- bcryptjs
- multer（封面图片上传，含文件魔数校验）

## 项目结构

```
community/
├── frontend/              # Vue3 前端（:3001）
│   ├── src/
│   │   ├── api/          # API 接口封装
│   │   ├── components/   # 公共组件
│   │   ├── views/        # 页面视图
│   │   ├── composables/  # 组合式函数
│   │   ├── router/       # 路由配置
│   │   ├── store/        # Pinia 状态管理
│   │   ├── utils/        # 工具函数
│   │   └── style.css     # 全局样式 + 设计令牌
│   └── vite.config.js
├── backend/               # Node.js 后端（:5000）
│   ├── src/
│   │   ├── config/       # 配置文件
│   │   ├── controllers/  # 控制器（薄，只做参数搬运）
│   │   ├── services/     # 业务逻辑与 SQL
│   │   ├── models/       # 数据模型
│   │   ├── routes/       # 路由
│   │   ├── utils/        # 工具函数（含上传文件的安全路径校验）
│   │   └── middleware/   # 中间件（鉴权 / 限流 / 上传）
│   ├── scripts/          # 运维脚本（封面清扫 / 日志留存清理 / 净化规则自检）
│   ├── uploads/          # 用户上传的封面（运行时数据，不进仓库）
│   └── server.js
├── scripts/               # Playwright + urllib 端到端验证脚本
└── database/              # 数据库脚本
    ├── schema.sql        # 表结构
    └── seed.sql          # 种子数据
```

## 开发建议

1. **先启动后端**，确保数据库连接正常
2. **再启动前端**，查看页面效果
3. **注册账号**后体验完整功能
4. **发布项目**测试 CRUD 功能

## 下一步计划

- [ ] 图片裁剪与压缩
- [ ] 安全事件目前只有后端与接口（`/logs/me/security`），还没有前端页面
- [ ] 把 `scripts/verify_*.py` 接入 CI
- [ ] 单元测试与覆盖率
- [ ] 移动端交互细节继续打磨

## 联系方式

如有问题，请提交 Issue 或联系开发者。
