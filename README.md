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
- [x] 发布 / 编辑项目页面（含封面图片上传：点击或拖拽、外链兜底，**大图先在本机压缩再上传**、**可拖动调整构图**）
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
- [x] 账号安全页（`/security`）—— 把「针对我的失败尝试」与「我的操作」搬上界面，含类型筛选与聚合次数

### 待完善的功能

⏳ **需要进一步完善**
- [x] ~~单元测试~~ 已落地：`backend/tests/unit/`（node:test 49 项），`npm test` 跑、`npm run test:coverage` 看覆盖率，CI 在安装依赖后最先执行

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

## 图片上传前的压缩

手机拍的原图动辄 6~10MB，而服务端上限是 5MB。旧流程会把用户直接挡回去
（「图片不能超过 5MB，请压缩后再上传」），等于让用户自己去找工具压一遍 ——
现在改成：**选图后先在本机 canvas 降采样 + 重新编码，用户无感**
（`frontend/src/utils/imageCompress.js`）。

三条边界是刻意设计的，做坏了比不做更糟：

| 场景 | 处理 | 为什么 |
| --- | --- | --- |
| 大图 | 长边降到 1920、转 WebP（q = 0.82） | 实测 9.5MB 原图 → 1.5MB，才过得了 5MB 闸门 |
| 小图 | **原样上传**，不做重编码 | 重编码会把一张 30KB 的图变成 60KB —— 越弄越糟 |
| GIF | **完全不动** | canvas 只能画第一帧，重编码会把动图压成一张静图，丢的是内容 |

压缩是「尽力而为」：解不出来（冷门格式 / 损坏文件）就原样放行，交给原有的类型 /
体积校验去给结论；压完反而更大的（原图已经精压过）也保留原图。
体积校验挪到了压缩**之后** —— 压完还超限才算真的超限。

⚠️ 客户端压缩 ≠ 放开服务端：`backend/src/middleware/upload.js` 的 5MB 上限、MIME 白名单
与文件头魔数校验一个都没动，直接 POST 超限内容仍然是 400。

### 验证

```bash
python scripts/verify_cover_compress.py   # 大图被压 / 小图原样 / GIF 不动 / 服务端闸门未放松
python scripts/verify_cover_crop.py       # 构图：几何单测（node 跑真函数）+ 拖到左右各只得一色
```

脚本里的压缩常量是从 `imageCompress.js` **源码读回来**的，而不是把 1920 抄进断言 ——
抄一份就等于「测试与实现各写一份」，常量改了测试照样绿、而功能已经不按预期工作了。

## 封面构图（把 16:9 里留下什么交给用户）

封面在卡片里按 **16:9** 展示（`ProjectCard.vue`）、在详情页头图里按 **21:9** 展示
（`ProjectDetailView.vue`），两处都是 `object-cover` —— 填满容器、溢出裁掉。
一张竖版手机照在这种容器里会被 CSS 从正中间横切一刀，主体常常正好落在被切掉的部分。
上一轮解决了「传得上来」，这一轮解决「显示成什么」：预览上多一个 **调整构图**，
点开是一个 16:9 的取景框，拖动图片决定留下哪一块（可缩放）。几何在
`frontend/src/utils/imageCrop.js`，界面在 `frontend/src/components/CoverCropper.vue`。

取景框按**最窄**的那个展示位（卡片 16:9）而不是更宽的 21:9，理由是 `object-cover` 只裁不补，
不存在能同时铺满两者的比例。取较窄的那个，任何展示位都不会切掉用户刚刚框定的**左右**内容 ——
详情页只是把上下再收一点，这正是横幅该有的行为；反过来若按 21:9 裁剪，卡片会把用户框好的
两侧吃掉，等于让用户白框一次。（数字上：按 16:9 裁，详情页约再收 24% 高度；按 21:9 裁，
卡片要把宽度砍掉 24%。）

三条守卫，每条都是「不做会更糟」：

| 情况 | 处理 | 为什么 |
| --- | --- | --- |
| 站内上传的封面 | 给入口 | 同源资源不会污染 canvas，`toBlob` 才拿得到结果 |
| 手填的图片地址 | **不给入口** | 外链跨源会污染画布，导出直接抛 `SecurityError` |
| GIF 封面 | **不给入口** | canvas 只画得出第一帧，裁一次就把动图静默变成静帧 |

其它几个刻意的选择：

- **不点裁剪就一个字节都不动**：裁剪是可选的，原图照旧原样上传（与压缩的「小图原样放行」同一条纪律）。
- **反复调整始终从原图出发**：裁完会重新上传并换掉封面地址，但组件记着本轮那张原图，
  下一次打开取景框仍以它为素材。否则每调一次就再切一刀，用户想「往回收一点」时已经收不回来了。
- **取消什么都不改**：不产生上传，封面地址保持原样。

### 验证

```bash
python scripts/verify_cover_crop.py       # 51 项：几何 + 端到端 + 守卫
```

两条最有分量的设计：

1. **几何断言跑的是真实现**。脚本把 `imageCrop.js` 复制成 `.mjs` 交给 node 直接调用，覆盖
   铺满取景框 / 居中即 `object-cover` 的中带 / 缩放按平方收缩 / 平移夹取 /
   全域扫描（5 档缩放 × 169 组偏移）永不越界 / 六种源图比例下输出比例恒定 /
   取景框像素尺寸无关性。在 Python 里另写一份公式对答案是不行的 —— 那种测试在实现写错时照样绿。
   （因此该模块刻意保持零 `import`，脚本把它也钉成一条断言。）
2. **用带方位标记的图反推裁剪结果**：左半红 / 右半蓝、顶部绿条 / 底部黄条。
   拖到最右只能看到红、拖到最左只能看到蓝、竖直方向既没有绿也没有黄 ——
   三条同时成立，才说明取景框真的落在用户框的地方，且竖直方向取的是正中那一条。

⚠️ 一轮约 7 次上传，而后端 `uploadLimiter` 是 40 次 / 15 分钟；连跑 5 轮左右会开始收到 429
（症状：某一次上传失败 → 没有封面 → 没有裁剪入口）。重启后端即可清零。

## 评论：假「加载更多」与孤儿回复

评论列表是「根评论分页 + 回复挂在根下」。巡检时探针实测出两个真 bug：

1. **假「加载更多」**：`total` 含回复，分页却只翻根评论。前端拿 `total` 判断还有没有下一页，
   结果只要有回复，「显示更多评论」永远点不完（点了 N 次后列表已到底，按钮还在）。
   修复：接口新增 `rootTotal`（只数 `parent_id IS NULL`），前端 `hasMore` 改按它算。
2. **孤儿回复**：`project_comments` 的自引用级联外键（删根评论带走其下回复）只存在于线上库
   （`ibfk_3`），`schema.sql` 里漏了 —— 谁拿 schema 重建库，删根评论就会留下一批
   永远不可见却污染 `total` 分页的孤儿行。修复：schema 补上
   `FOREIGN KEY (parent_id) REFERENCES project_comments(id) ON DELETE CASCADE`。

### 验证

```bash
python scripts/verify_comments.py         # 41 项：CRUD / 权限矩阵 / rootTotal 分家 / 级联零孤儿 / 页面交互
python scripts/verify_replies.py          # 两级结构与展平（7 项）
python scripts/verify_comment_likes.py    # 点赞（9 项）
python scripts/verify_comment_deeplink.py # 深链定位（24 项）
```

`verify_comments.py` 的分页红线值得说明：造 12 根 + 1 回复（`total=13 ≠ rootTotal=12`），
游客翻完第 2 页后断言按钮消失 —— 旧代码 `12 < 13` 按钮残留，新代码 `12 < 12` 即消失。
红证方式：把服务端 `rootTotal` 临时换回 `total`，两条分页断言立刻变红。

## 标签：超长从静默截断到明确拒绝

标签上限 12 字，此前前后端各自静默 `.slice(0, 12)`——15 字标签提交成功后悄悄变成残缺，
用户毫无感知，而标题/介绍/评论全站都是「超长 400」。2026-09 产品决策：**与全站对齐，明确拒绝**。

- 后端 `normalizeTags`：剥 emoji → 收敛空白后**超过 12 字直接 400**（提示「单个标签最多 12 个字符」）。
  与评论同哲学：净化后才算长度，emoji 不占额度。
- 前端输入框本就有 `maxlength=12`（键盘/粘贴当场可见地被截住）；`cleanTag` 的兜底 slice 一并移除
  ——绕过输入框的路径交给后端 400，不再有任何一处静默截断。
- 提示文案补上「单个最多 12 字」。

### 验证

```bash
python scripts/verify_project_tags.py      # 30 项：含 13 字 400 / 12 字放行 / emoji 剥后算长度 / 发布页 maxlength
python scripts/verify_project_edit.py      # 51 项：超长期望已从「截断」翻转为「拒绝」，编辑路径不受影响
```

## 浏览量：登录用户终身去重

此前每次详情请求都 +1，同一用户刷新 10 次就 +10，刷量零成本。现按登录用户**终身去重**：
`project_views(project_id, user_id)` 复合主键表占位，只有真正新插入（首访）才自增浏览量；
游客无身份不落表，照旧每次 +1。并发首访由主键兜底——8 个并发请求也只有一条 INSERT 能通过，
恰好 +1（`findOrCreate` 靠唯一键回头重读，不重复自增）。

- 列类型按线上遗留结构用 `INT UNSIGNED`（与 `project_favorites` 同例）；
  FK 级联：删项目/删用户时去重行随之清理
- 自增仍走 SQL 层 `literal`，读改写并发丢更新的老坑不回归
- 去重表故障不阻塞详情响应（退化为不计本次浏览）

### 验证

```bash
python scripts/verify_view_count.py        # 28 项：计数语义 / 去重矩阵 / 并发首访恰 +1 与游客并发恰 +8 / 404 / 展示层
```

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

### 前端页面（`/security`）

两条只读接口在界面上合成了**一页两个视图**（顶栏用户菜单「账号安全」，或个人中心里的入口进）：

| 视图 | 数据源 | 回答的问题 |
| --- | --- | --- |
| 安全提醒 | `GET /logs/me/security` | 谁在打我账号的主意 |
| 我的操作 | `GET /logs/me` | 我自己做过什么 |

⚠️ 页面上刻意**只列两类事件**做筛选（登录 / 注册），不放 `auth.token.rejected`：伪造令牌的尝试
在写事件时拿不到可信身份，`target_user_id` 是 NULL，而 `listMine` 按 `target_user_id = 我` 过滤 ——
它**永远**查不到这类行。给它一个筛选项，就等于给用户一个**永远筛出空列表的假入口**。
这条口径由 `verify_security_page.py` 直接断言（**每个筛选 chip 都必须真能筛出行来**），
并且顺带断言前端词表的键集合覆盖后端白名单。

列表行**不重复动作名**：后端的 `summary` 本来就以动词开头（`发布项目「X」`），再摆一个「发布项目」
的 chip 就是在同一行里说两遍 —— 所以动作名只出现在筛选 chip 里，列表行靠图标 + 句子表达。

`frontend/src/utils/audit.js` 是「枚举值 → 中文」的词表（前端唯一口径）。它必须覆盖后端白名单：
值写错**不会报错**，只会静默落到兜底文案「异常尝试」，于是整类事件显示错都不会有人发现。

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
python scripts/verify_security_page.py       # 前端页：渲染 / 筛选（无假入口）/ 空状态 / 脱敏不上屏（60 项）
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

「坏输入 × 全端点」矩阵（1000 项断言），与 `scripts/audit_frontend_ui.py` 互补：
前端巡检管「页面长得对不对」，它管「接口在坏输入下会不会把 500 甩给用户」。五条不变量：

1. 任何**用户可控输入**都不得产生 5xx —— 能预见的坏输入必须是 4xx；
2. 所有响应恒为 `{code, message, data?}`，且 `code === HTTP 状态码`；
3. 所有 4xx 的 `message` 必须是中文人话，不含英文技术原文；
4. 受保护端点无 token / 坏 token 一律 401（不是 500，也不是 200）；
5. 方法不匹配 / 路由不存在一律 404（不是 500）。

⚠️ 请求量较大，**请单独跑**，不要与其它验证脚本并跑 —— 否则会撞全局限流（600 次 / 15 分钟）把结果染红。
撞了重启后端即可清零（`express-rate-limit` 用内存计数）。

## 验证套件与 CI

28 个验证脚本不用一个个手敲：`scripts/run_verify_suite.py` 顺序跑全量并汇总，
任一失败 exit 1。脚本间自动重启后端清限流（仅当后端由套件自己拉起；复用本机
现役服务时不动它）。解释器注意：脚本继承**启动套件的 python**，它必须装有
playwright（本地用带 playwright 的完整路径解释器启动，或设 `VERIFY_PYTHON`）。

```bash
python scripts/run_verify_suite.py --list              # 28 个脚本清单
python scripts/run_verify_suite.py --only verify_tags  # 定向跑（.py 可省）
python scripts/run_verify_suite.py                     # 全量 + 汇总
```

接入 CI（`.github/workflows/verify.yml`）：push / PR / 手动触发 → 全新 ubuntu +
MySQL 8.4 service → 建库种子 → `run_verify_suite.py` 全量 → 失败时上传
`suite-server.log` 与截图现场。凭据双层注入：`DB_*` 给 backend 与 seed.js，
`VERIFY_*` 给 `_verify_common.py`（本仓库工具层已环境变量化，本地不设变量时
行为与历史逐字节一致）。首次 CI 全量跑可能暴露个别脚本对种子数据的隐式假设——
那属于修脚本，不是修 CI。

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

- [x] ~~移动端交互细节继续打磨~~ 已落地：44px 触屏热区（伪元素扩展，视觉零变化）、
  双击缩放防线（touch-action: manipulation）、iOS 聚焦缩放防线（小屏输入 16px）
- [x] ~~深色模式逐页走查~~ 已落地：写死 hex 全部收敛到设计令牌（点赞/徽章红 → clay、
  success 绿新增 --c-green 双主题令牌），逐页 console/溢出/令牌色值断言入 `verify_dark_mode.py`
- [x] ~~评论 @ 提及~~ 已落地：解析（@ 到标点/空白止、2-20 字符、静默忽略不存在的名字、
  作者自排除）→ mention 通知（独立于评论/回复，带 commentId 深链）→ 评论高亮
  （后端整库识别口径下发 mentionNames，前端零 v-html 纯插值）→ 行尾 @ 补全浮层；
  富文本排版另立一轮（涉及 XSS 白名单）
- [ ] 评论富文本排版（粗体/代码块，sanitize 白名单）

## 深色模式逐页走查

深色主题（`prefers-color-scheme: dark` 令牌翻转）此前骨架健全，但组件层有 3 处
写死 hex 绕过令牌——深色下不随主题翻转。本轮全部收敛：

- **点赞激活红 / 未读徽章红**：`#FF3B30` → `clay` 令牌（深色 #FF453A 即 iOS dark
  systemRed），同一「红色语义」单令牌——点赞按钮 hover 态本来就是 clay，激活态却是
  写死值，同组件双口径是漂移的活证
- **success 提示绿**：新增 `--c-green` 双主题令牌（浅 #34C759 / 深 #30D158，
  iOS systemGreen），tailwind 注册 `green` 色，ToastHost success 分支改走令牌
- 验证：`scripts/verify_dark_mode.py` —— 断言全部「钉死到具体令牌」（读
  getComputedStyle 与令牌期望值全等比较，不用「看起来像深色」的主观谓词）；
  深色逐页 console 零错误 + 无横向溢出；深浅两主题对照（红证 5 条全落病灶处）

## 评论 @ 提及

评论里 `@用户名` 可以点名用户：被提及的人收到独立于评论/回复的 `mention` 通知
（带 commentId 深链到那条评论），正文里的 @名字 渲染成高亮。

- **识别口径**（唯一事实：`backend/src/services/comment.service.js` 的
  `extractMentionNames` / `resolveMentions`）：@ 到空白或常见标点为止，2-20 字符；
  查不到的用户名**静默忽略**（@ 错名字不拦评论发布）；作者 @ 自己不通知
- **高亮口径**：后端 listComments 顶层下发 `mentionNames`（整页候选名一次查库、
  只有真实存在的用户名才进集合），前端 `CommentContent.vue` 纯文本插值高亮
  （无 v-html，XSS 面 = 0）——两端同口径，不会假高亮
- **补全**：输入框行尾输入 `@` 弹出候选浮层（本页评论作者去重、排除自己、片段过滤），
  点选插入；句中 @ 不弹浮层但打全名仍会被识别（textarea 无 caret 检测的轻量近似）
- 通知 ENUM 扩展：`notifications.type` 加 `'mention'`（模型 / schema.sql / 线上表三处同步）
- 验证：`scripts/verify_mentions.py` 18 项（解析/通知/排除/深链/高亮/文案/补全/过滤）
  + 回归 verify_comments 41 项、verify_notifications、单测 49 项

## 移动端触控细节

触屏可用性三防线，全部「视觉零变化」：

- **44px 热区**：卡片收藏（28→44）、评论行内按钮（~24→44，只扩垂直——水平扩展
  会互吃相邻按钮热区）、分页按钮（36→52 垂直）、header 铃铛/账号菜单（36/40→48）。
  实现：`::after` 伪元素扩展命中区（`after:-inset-2` 一类），视觉盒不变
- **双击缩放**：全局 `button, a, [role='button'] { touch-action: manipulation }`，
  快速连点收藏/点赞不触发页面缩放
- **iOS 聚焦缩放**：输入字号 < 16px 时 iOS Safari 聚焦会自动放大整个页面；
  小屏（≤640px，与 sm 断点一致）输入类统一 16px，桌面视觉不变

```bash
python scripts/verify_mobile_touch.py   # 24 项：盒边外命中探测（elementFromPoint）+ 视觉盒不变 + 字号/触控行为
```

⚠️ 探测点必须以「盒边」为基准且探测前 `scrollIntoView({block:'center'})`——
贴边滚入或以盒心为基准都会假红/假绿（实测踩过）。

## 联系方式

如有问题，请提交 Issue 或联系开发者。
