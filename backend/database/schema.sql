-- ============================================================================
-- 共创社区 · 建库脚本（新环境唯一起点）
-- ============================================================================
--
-- 作用：在一台空 MySQL 8.4 上建出**与生产同构**的库。
--
-- 这份文件是「什么结构才算正确」的事实源之一，另两个是：
--   · 线上库（information_schema）
--   · backend/src/models/ 下的 Sequelize 模型
-- 三方必须一致 —— scripts/verify_schema_consistency.py 把它钉成可执行断言。
--
-- ---------------------------------------------------------------------------
-- ⚠️ 为什么这份文件值得单独钉一遍（2026-10-02 实测发现的三类致命错误）
-- ---------------------------------------------------------------------------
-- 这份文件此前**从未被真正执行过**：校验脚本只用正则解析它（且只比对表名与索引），
-- 于是同时藏着三处会让新环境建库直接失败的写法，且全部静默通过校验：
--
--   1. categories 的列定义缺一个逗号、索引行尾又多一个逗号 → ERROR 1064
--      （错误的位次恰好是上一轮「补 idx_name 索引」时手滑，属回归）
--   2. comment_likes / notifications 引用了**声明在它们后面**的 project_comments
--      → ERROR 1824（MySQL 要求被引用表先建）
--   3. 各 id 列有符号 INT 与无符号 INT UNSIGNED 混用，而线上统一是 UNSIGNED；
--      混用会让外键直接建不起来 → ERROR 3780
--
-- 教训：**「能解析」不等于「能执行」**。脚本里现在有一条 S11 断言，会把这份文件
-- 真的喂给 MySQL 跑一遍（全是 IF NOT EXISTS，对既有库无副作用）。
--
-- ---------------------------------------------------------------------------
-- 两点**有意**与线上不同，除此之外逐列一致（理由在此，别当漏写）
-- ---------------------------------------------------------------------------
--   1. updated_at 写成 `DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP`。
--      线上那批表是 `DEFAULT '0000-00-00 00:00:00'` 且无 ON UPDATE —— 零日期默认值
--      在 MySQL 8 默认 sql_mode（含 NO_ZERO_DATE）下建表会被直接拒绝，属不可移植写法。
--      实际影响为零：Sequelize 每次 save 都显式写 updated_at，ON UPDATE 永不触发。
--   2. 统一 COLLATE utf8mb4_unicode_ci（线上 project_views 是 utf8mb4_0900_ai_ci，
--      该表只有 int / timestamp，没有文本列，两者等价），并修正了线上因历史编码问题
--      而乱码的表注释（如「åˆ†ç±»è¡¨」→「分类表」）。
--
-- 执行（目标库在命令里指定，本文件不含 CREATE DATABASE / USE，不写死库名）：
--   mysql -u<用户> -p <库名> < backend/database/schema.sql
--   node backend/database/seed.js        # 写入 8 条分类种子
--
-- 「线上遗留列」说明：users.status/is_admin、categories.project_count/status、
-- projects.status/repository_url/end_date/access_type/access_password 这些列在线上
-- 确实存在（部分还有真实数据），但当前代码库零读写。保留声明是为了让新环境建库
-- 结果与生产**逐列一致**；启用还是清理属产品决策，详见 docs/功能与数据设计审计报告.md。
-- ============================================================================


-- ---------------------------------------------------------------------------
-- 用户表
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '用户ID',
    username VARCHAR(50) NOT NULL COMMENT '用户名',
    email VARCHAR(100) NOT NULL COMMENT '邮箱',
    -- 列名是 password，存的是 bcrypt 哈希（Sequelize 模型侧映射为 password_hash）
    password VARCHAR(255) NOT NULL COMMENT '密码(bcrypt 哈希)',
    avatar VARCHAR(255) DEFAULT NULL COMMENT '头像URL',
    bio TEXT COMMENT '个人简介',
    -- 【线上遗留】有数据（1 个管理员、38 行 status=1），但全仓零读写：
    -- 本项目还没有角色体系，也没有账号停用流程。
    status TINYINT DEFAULT 1 COMMENT '状态: 1-正常, 0-禁用（线上遗留，代码未使用）',
    is_admin TINYINT DEFAULT 0 COMMENT '是否管理员: 1-是, 0-否（线上遗留，代码未使用）',
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    UNIQUE KEY username (username),
    UNIQUE KEY email (email),
    -- 以下两条与上面的唯一键**列相同**：唯一键已能服务等值查询。保留是为了与线上
    -- 结构逐字一致（线上确有这两条冗余索引），不要在「优化索引」时顺手删掉。
    KEY idx_email (email),
    KEY idx_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';


-- ---------------------------------------------------------------------------
-- 分类表（8 条种子由 backend/database/seed.js 提供，不写死在这里）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS categories (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '分类ID',
    name VARCHAR(50) NOT NULL COMMENT '分类名称',
    icon VARCHAR(50) DEFAULT NULL COMMENT '图标名称',
    -- 线上是 VARCHAR(255) 而不是 TEXT：写超长描述会被数据库截断，别按 TEXT 用
    description VARCHAR(255) DEFAULT NULL COMMENT '分类描述',
    sort_order INT DEFAULT 0 COMMENT '排序顺序',
    -- 【线上遗留】已填值但全仓零读写：分类下项目数目前是列表查询实时 count 出来的，
    -- 没有物化回这一列。
    project_count INT DEFAULT 0 COMMENT '项目数量（线上遗留，代码未使用）',
    status TINYINT DEFAULT 1 COMMENT '状态: 1-启用, 0-禁用（线上遗留，代码未使用）',
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    -- ⚠️ 唯一键 name 是 seed.js 的 `INSERT ... ON DUPLICATE KEY UPDATE` 能**幂等重跑**
    -- 的前提（否则每跑一次 seed 就多 8 条重复分类）。它和下面的 idx_name 列相同但
    -- 语义不同，两个都要留。
    UNIQUE KEY name (name),
    KEY idx_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='分类表';


-- ---------------------------------------------------------------------------
-- 项目表
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projects (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '项目ID',
    title VARCHAR(200) NOT NULL COMMENT '项目标题',
    description TEXT NOT NULL COMMENT '项目描述',
    cover_image VARCHAR(255) DEFAULT NULL COMMENT '封面图片URL',
    -- NOT NULL：接口层 assertCategoryExists 会把空分类挡在 400，前端也标了必选
    category_id INT UNSIGNED NOT NULL COMMENT '分类ID',
    creator_id INT UNSIGNED NOT NULL COMMENT '创建者ID',
    participant_count INT DEFAULT 0 COMMENT '参与人数',
    like_count INT DEFAULT 0 COMMENT '点赞数',
    comment_count INT DEFAULT 0 COMMENT '评论数',
    view_count INT DEFAULT 0 COMMENT '浏览量',
    is_recommend TINYINT DEFAULT 0 COMMENT '编辑推荐: 1-是, 0-否',
    -- is_hot 已废弃：全仓无代码写入，热门语义改由 sort=hot（按 like_count 排序）承担。
    -- 保留该列仅为与线上结构一致，不要再新增读写。
    is_hot TINYINT DEFAULT 0 COMMENT '热门标记（已废弃，见上行注释）',
    -- 【线上遗留】线上默认 1、注释为「1-进行中/2-已完成/0-已下架」，但全仓零读写：
    -- 目前没有项目状态机与草稿箱，发布即上线。列定义以线上为准。
    status TINYINT DEFAULT 1 COMMENT '状态: 1-进行中, 2-已完成, 0-已下架（线上遗留，代码未使用）',
    -- 标签的唯一真源。CHARACTER SET utf8mb4_bin 是为了让 JSON_CONTAINS 按码点精确
    -- 匹配而不是按 collation 模糊匹配（否则「AI」可能匹配上「ai」）。
    tags LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_bin COMMENT '标签数组（JSON 字符串）',
    -- 【线上遗留】repository_url 线上甚至有 10 个项目在用，但全仓零读写 ——
    -- 不是「功能没做完」，是这个字段没有任何代码碰过。end_date / access_type /
    -- access_password 同理（access_password 线上全为空）。
    repository_url VARCHAR(255) DEFAULT NULL COMMENT '仓库地址（线上遗留，代码未使用）',
    end_date DATE DEFAULT NULL COMMENT '截止日期（线上遗留，代码未使用）',
    access_type VARCHAR(20) DEFAULT 'public' COMMENT '访问类型: public/password/private（线上遗留，代码未使用）',
    access_password VARCHAR(255) DEFAULT NULL COMMENT '访问密码（线上遗留，代码未使用）',
    deleted_at TIMESTAMP NULL DEFAULT NULL COMMENT '删除时间(软删除)',
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    KEY idx_category (category_id),
    KEY idx_creator (creator_id),
    KEY idx_status (status),
    -- 列表最高频的三个排序入口：默认「最新」、sort=hot、sort=participants。
    -- 缺了它们，ORDER BY 每次都是全表 filesort，数据量上来后性能断崖。
    KEY idx_created (created_at),
    KEY idx_like_count (like_count),
    KEY idx_participant_count (participant_count),
    KEY idx_deleted_at (deleted_at),
    -- ⚠️ 线上这条外键**没有** ON DELETE 子句（即 RESTRICT），别想当然写成 SET NULL：
    -- 有项目挂着的分类删不掉，这是有意的约束。
    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (creator_id) REFERENCES users(id) ON DELETE CASCADE,
    -- tags 可能被旁路写入非 JSON（如直接改库）。服务层 normalizeTags 是第一道，
    -- 这条 CHECK 是最后一道，让脏数据根本进不来。
    CONSTRAINT projects_chk_1 CHECK (json_valid(`tags`))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目表';


-- ---------------------------------------------------------------------------
-- 项目评论表（parent_id 自引用形成回复树）
--
-- ⚠️ 本表必须声明在 comment_likes / notifications **之前**：那两张表的外键指向这里，
--    而 MySQL 要求被引用表先存在，否则建库直接 ERROR 1824。这是本文件曾经的真实故障。
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS project_comments (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '评论ID',
    project_id INT UNSIGNED NOT NULL COMMENT '项目ID',
    user_id INT UNSIGNED NOT NULL COMMENT '用户ID',
    parent_id INT UNSIGNED DEFAULT NULL COMMENT '父评论ID(用于回复)',
    content TEXT NOT NULL COMMENT '评论内容',
    like_count INT DEFAULT 0 COMMENT '点赞数',
    status TINYINT DEFAULT 1 COMMENT '状态: 1-正常, 0-隐藏',
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    KEY idx_project (project_id),
    KEY idx_user (user_id),
    KEY idx_parent (parent_id),
    -- parent_id 的自引用级联外键（删根评论时由 InnoDB 带走其下全部回复）。
    -- 它此前只存在于线上库（ibfk_3）、本文件漏了：谁拿 schema.sql 重建库，
    -- 删根评论就会静默留下一批永远不可见却污染 total 分页的孤儿回复。
    FOREIGN KEY (parent_id) REFERENCES project_comments(id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目评论表';


-- ---------------------------------------------------------------------------
-- 评论点赞表（复合主键即唯一键，数据库层防重复点赞；评论删除时级联清理）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS comment_likes (
    comment_id INT UNSIGNED NOT NULL,
    user_id INT UNSIGNED NOT NULL,
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (comment_id, user_id),
    KEY user_id (user_id),
    FOREIGN KEY (comment_id) REFERENCES project_comments(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='评论点赞表';


-- ---------------------------------------------------------------------------
-- 站内通知表（评论/回复/点赞/参与/@提及触发；相关评论删除时级联清理）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id INT UNSIGNED NOT NULL COMMENT '接收人',
    actor_id INT UNSIGNED NOT NULL COMMENT '触发者',
    -- mention：评论内容里 @ 到了用户（comment.service 的 extractMentions）
    type ENUM('comment', 'reply', 'like', 'participate', 'mention') NOT NULL,
    project_id INT UNSIGNED NOT NULL,
    comment_id INT UNSIGNED DEFAULT NULL,
    is_read TINYINT DEFAULT 0,
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    -- ⚠️ PRIMARY KEY (id) 不能漏：AUTO_INCREMENT 列必须被定义为键，
    -- 漏了会 ERROR 1075，而 IF NOT EXISTS 在已存在的库上会静默跳过、只在全新环境才炸
    PRIMARY KEY (id),
    -- 未读数查询（user_id + is_read）与列表倒序共用这条联合索引
    KEY idx_user_read (user_id, is_read, created_at),
    KEY actor_id (actor_id),
    KEY project_id (project_id),
    KEY comment_id (comment_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (actor_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (comment_id) REFERENCES project_comments(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='通知表';


-- ---------------------------------------------------------------------------
-- 项目收藏表
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS project_favorites (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '记录ID',
    project_id INT UNSIGNED NOT NULL COMMENT '项目ID',
    user_id INT UNSIGNED NOT NULL COMMENT '用户ID',
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP COMMENT '收藏时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_project_user (project_id, user_id),
    KEY idx_user (user_id),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目收藏表';


-- ---------------------------------------------------------------------------
-- 项目点赞表（唯一键防重复点赞）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS project_likes (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '记录ID',
    project_id INT UNSIGNED NOT NULL COMMENT '项目ID',
    user_id INT UNSIGNED NOT NULL COMMENT '用户ID',
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP COMMENT '点赞时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_project_user (project_id, user_id),
    KEY idx_user (user_id),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目点赞表';


-- ---------------------------------------------------------------------------
-- 项目参与者表
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS project_participants (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '记录ID',
    project_id INT UNSIGNED NOT NULL COMMENT '项目ID',
    user_id INT UNSIGNED NOT NULL COMMENT '用户ID',
    -- 线上是 VARCHAR(50) 而不是 ENUM：Sequelize 模型侧声明了 ENUM，但库上没有约束，
    -- 也就是说非法 role 目前只靠代码自律。收紧成 ENUM 是独立的一次迁移，别混在这里做。
    role VARCHAR(50) DEFAULT 'member' COMMENT '角色: creator-创建者, member-成员',
    joined_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP COMMENT '加入时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_project_user (project_id, user_id),
    KEY idx_user (user_id),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目参与者表';


-- ---------------------------------------------------------------------------
-- 浏览去重表（登录用户终身去重：同一用户对同一项目只计 1 次浏览量；
-- (project_id,user_id) 主键兜底并发首访；游客无身份不落此表、照旧每次 +1）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS project_views (
    project_id INT UNSIGNED NOT NULL,
    user_id INT UNSIGNED NOT NULL,
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (project_id, user_id),
    KEY user_id (user_id),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='浏览去重表';


-- ---------------------------------------------------------------------------
-- 操作日志表（审计留痕：发布内容、编辑、删除、评论等写操作）
-- 刻意**不建外键**：日志必须比它描述的对象活得久。本仓库的删除链路是
-- users -> projects -> project_comments 一路 ON DELETE CASCADE，一旦这里挂外键，
-- 注销账号就会把证据一并删掉 —— 偏偏那是最需要留痕的场景。
-- 因此只存 id + 名称快照，代价是可能出现「孤儿日志」，这对审计来说是特性。
-- 文本字段的净化规则见 backend/src/utils/logSanitize.js（防 CRLF 伪造/控制字符/超长）。
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS activity_logs (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id INT UNSIGNED DEFAULT NULL COMMENT '操作者ID（无外键）',
    username VARCHAR(50) DEFAULT NULL COMMENT '操作者名称快照（已净化：单行、无控制字符）',
    action VARCHAR(32) NOT NULL COMMENT '动作标识（project.create 等，服务层白名单约束）',
    target_type VARCHAR(20) NOT NULL COMMENT '目标类型：project / comment / user',
    target_id INT UNSIGNED DEFAULT NULL COMMENT '目标ID',
    project_id INT UNSIGNED DEFAULT NULL COMMENT '所属项目ID',
    summary VARCHAR(255) NOT NULL COMMENT '单行摘要（已净化，无换行与控制字符）',
    detail JSON DEFAULT NULL COMMENT '结构化附加信息（键受白名单约束）',
    ip VARCHAR(45) DEFAULT NULL COMMENT '来源IP',
    user_agent VARCHAR(255) DEFAULT NULL COMMENT '客户端标识（已净化并截断）',
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_user_time (user_id, created_at),
    KEY idx_project_time (project_id, created_at),
    KEY idx_action_time (action, created_at),
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='操作日志表';


-- ---------------------------------------------------------------------------
-- 安全事件表（被拒的尝试：登录失败、注册被拒、令牌无效）
-- 与 activity_logs 刻意分开：那边记「谁做成了什么」（有身份、可逐条读），
-- 这边记「有人尝试但没成功」（大多没有身份），合表会让用户自己的时间线被攻击噪音灌满。
-- 同样**不建外键**。三条硬约束：
--   1. 绝不记密码（任何形态）；
--   2. account 列只存**脱敏**后的账号标识，不存明文邮箱；
--   3. 按 fingerprint + 时间窗口**聚合**（occurrences / last_seen_at），
--      否则「同一来源反复失败」这一本质特征会变成海量重复行。
-- 写入入口唯一：backend/src/services/securityEvent.service.js
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS security_events (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    event VARCHAR(40) NOT NULL COMMENT '事件标识（auth.login.rejected 等，服务层白名单约束）',
    reason VARCHAR(120) NOT NULL COMMENT '被拒原因（系统文案，已净化）',
    target_user_id INT UNSIGNED DEFAULT NULL COMMENT '被尝试的目标账号ID（仅当账号存在）',
    account VARCHAR(80) DEFAULT NULL COMMENT '被尝试的账号标识（已脱敏，不存明文）',
    ip VARCHAR(45) DEFAULT NULL COMMENT '来源IP',
    user_agent VARCHAR(255) DEFAULT NULL COMMENT '客户端标识（已净化并截断）',
    path VARCHAR(120) DEFAULT NULL COMMENT '接口路径（不含 query）',
    method VARCHAR(10) DEFAULT NULL COMMENT 'HTTP 方法',
    fingerprint VARCHAR(64) NOT NULL COMMENT '聚合键 sha256(event|ip|account|targetUserId|path)',
    occurrences INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '窗口内被合并的尝试次数',
    -- ⚠️ 必须是 TIMESTAMP 而不是 DATETIME：Sequelize 把连接会话时区固定成 +00:00，
    -- 于是它写进去的 DATETIME 是**裸 UTC 值**，而 created_at（TIMESTAMP）是时区感知的 ——
    -- 在 mysql CLI（会话 +08:00）里看同一行，两列会差 8 小时，连 SQL 里直接比较都会得出
    -- 错误结论。这坑是实测踩到的（验证脚本的「last_seen_at 不早于 created_at」断言报错）。
    -- 统一成 TIMESTAMP，任何会话里两列都自洽。
    last_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '最近一次发生时间（窗口按它计算）',
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    -- 聚合窗口查询（fingerprint + last_seen_at）是最高频路径
    KEY idx_fingerprint_time (fingerprint, last_seen_at),
    KEY idx_event_time (event, created_at),
    KEY idx_ip_time (ip, created_at),
    KEY idx_target_time (target_user_id, last_seen_at),
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='安全事件表（被拒的尝试，已聚合）';


-- ---------------------------------------------------------------------------
-- 关于「标签表」：这里曾经声明过 tags / project_tags 两张表并配了 Tag / ProjectTag
-- 模型，但它们从未被任何 service 读写过（线上库里也从未创建），属于纯粹的 schema
-- 漂移 —— 新环境照这份文件建库会多出两张与真实数据不一致的死表。已删除。
-- 标签的唯一真源是 projects.tags（LONGTEXT，存 JSON 数组字符串），见上方注释。
-- ---------------------------------------------------------------------------
