-- ============================================================
-- 共创社区平台 数据库结构
-- 与 backend/src/models 中的 Sequelize 模型定义保持一致
--
-- ⚠️ 库名以 backend/.env 的 DB_NAME 为准（当前为 co_creation_esdk）。
-- 下面两行的默认值只在「全新环境从零初始化」时用于建库；已部署的环境请勿
-- 直接整文件执行，否则会新建出一个空库：
--   mysql -u<用户> -p <库名> < database/schema.sql   # 或按需摘取单条 DDL
-- ============================================================

CREATE DATABASE IF NOT EXISTS co_creation_esdk CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE co_creation_esdk;

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL COMMENT 'bcrypt 加密后的密码',
    avatar VARCHAR(255) DEFAULT NULL,
    bio TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 分类表
CREATE TABLE IF NOT EXISTS categories (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL,
    icon VARCHAR(50) DEFAULT NULL,
    description TEXT DEFAULT NULL,
    sort_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 项目表
CREATE TABLE IF NOT EXISTS projects (
    id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    cover_image VARCHAR(255) DEFAULT NULL,
    category_id INT DEFAULT NULL,
    creator_id INT NOT NULL,
    status TINYINT DEFAULT 0 COMMENT '0-正常',
    tags TEXT DEFAULT NULL COMMENT 'JSON 数组字符串',
    is_recommend TINYINT DEFAULT 0 COMMENT '编辑推荐',
    is_hot TINYINT DEFAULT 0 COMMENT '热门标记',
    like_count INT DEFAULT 0,
    comment_count INT DEFAULT 0,
    participant_count INT DEFAULT 0,
    view_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP DEFAULT NULL COMMENT '软删除标记',
    INDEX idx_creator (creator_id),
    INDEX idx_category (category_id),
    INDEX idx_deleted_at (deleted_at),
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL,
    FOREIGN KEY (creator_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 标签表
CREATE TABLE IF NOT EXISTS tags (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 项目标签关联表
CREATE TABLE IF NOT EXISTS project_tags (
    project_id INT NOT NULL,
    tag_id INT NOT NULL,
    PRIMARY KEY (project_id, tag_id),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

-- 评论点赞表（唯一约束防止重复点赞；评论删除时级联清理）
CREATE TABLE IF NOT EXISTS comment_likes (
    comment_id INT UNSIGNED NOT NULL,
    user_id INT UNSIGNED NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (comment_id, user_id),
    FOREIGN KEY (comment_id) REFERENCES project_comments(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 项目参与者表
CREATE TABLE IF NOT EXISTS project_participants (
    project_id INT NOT NULL,
    user_id INT NOT NULL,
    role ENUM('creator', 'member', 'observer') DEFAULT 'member',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (project_id, user_id),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 项目点赞表（唯一约束防止重复点赞）
CREATE TABLE IF NOT EXISTS project_likes (
    project_id INT NOT NULL,
    user_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (project_id, user_id),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 项目收藏表（复用线上遗留结构：(project_id,user_id) 唯一键防重复收藏）
CREATE TABLE IF NOT EXISTS project_favorites (
    id INT UNSIGNED PRIMARY KEY AUTO_INCREMENT COMMENT '记录ID',
    project_id INT UNSIGNED NOT NULL COMMENT '项目ID',
    user_id INT UNSIGNED NOT NULL COMMENT '用户ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '收藏时间',
    UNIQUE KEY uk_project_user (project_id, user_id),
    KEY idx_user (user_id),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目收藏表';

-- 项目浏览去重表（登录用户终身去重：同一用户对同一项目只计 1 次浏览量；
-- (project_id,user_id) 主键兜底并发首访，游客无身份不落此表、照旧每次 +1。
-- 列类型按线上遗留结构用 INT UNSIGNED，与 project_favorites 同例）
CREATE TABLE IF NOT EXISTS project_views (
    project_id INT UNSIGNED NOT NULL,
    user_id INT UNSIGNED NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (project_id, user_id),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 站内通知表（评论/回复/点赞触发；相关评论删除时级联清理）
CREATE TABLE IF NOT EXISTS notifications (
    id INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    user_id INT UNSIGNED NOT NULL COMMENT '接收人',
    actor_id INT UNSIGNED NOT NULL COMMENT '触发者',
    type ENUM('comment','reply','like','participate') NOT NULL,
    project_id INT UNSIGNED NOT NULL,
    comment_id INT UNSIGNED DEFAULT NULL,
    is_read TINYINT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_read (user_id, is_read, created_at),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (actor_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (comment_id) REFERENCES project_comments(id) ON DELETE CASCADE
);

-- 项目评论表（复用线上遗留表结构：parent_id/like_count/status 暂未启用，按平铺列表展示）
CREATE TABLE IF NOT EXISTS project_comments (
    id INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
    project_id INT UNSIGNED NOT NULL,
    user_id INT UNSIGNED NOT NULL,
    parent_id INT UNSIGNED DEFAULT NULL COMMENT '父评论ID（回复功能预留）',
    content TEXT NOT NULL,
    like_count INT DEFAULT 0,
    status TINYINT DEFAULT 1 COMMENT '1-正常, 0-隐藏',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_project (project_id),
    INDEX idx_user (user_id),
    -- parent_id 的自引用级联外键（删根评论时由 InnoDB 带走其下全部回复）。
    -- 此前它只存在于线上库（ibfk_3）、本文件漏了：谁拿 schema.sql 重建库，
    -- 删根评论就会静默留下一批永远不可见却污染 total 分页的孤儿回复。
    INDEX idx_parent (parent_id),
    FOREIGN KEY (parent_id) REFERENCES project_comments(id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 操作日志表（审计留痕：发布内容、编辑、删除、评论等写操作）
-- 刻意**不建外键**：日志必须比它描述的对象活得久。本仓库的删除链路是
-- users -> projects -> project_comments 一路 ON DELETE CASCADE，一旦这里挂外键，
-- 注销账号就会把证据一并删掉 —— 偏偏那是最需要留痕的场景。
-- 因此只存 id + 名称快照，代价是可能出现「孤儿日志」，这对审计来说是特性。
-- 文本字段的净化规则见 backend/src/utils/logSanitize.js（防 CRLF 伪造/控制字符/超长）。
CREATE TABLE IF NOT EXISTS activity_logs (
    id INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_time (user_id, created_at),
    INDEX idx_project_time (project_id, created_at),
    INDEX idx_action_time (action, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='操作日志表';

-- 安全事件表（被拒的尝试：登录失败、注册被拒、令牌无效）
-- 与 activity_logs 刻意分开：那边记「谁做成了什么」（有身份、可逐条读），
-- 这边记「有人尝试但没成功」（大多没有身份），合表会让用户自己的时间线被攻击噪音灌满。
-- 同样**不建外键**。三条硬约束：
--   1. 绝不记密码（任何形态）；
--   2. account 列只存**脱敏**后的账号标识，不存明文邮箱；
--   3. 按 fingerprint + 时间窗口**聚合**（occurrences / last_seen_at），
--      否则「同一来源反复失败」这一本质特征会变成海量重复行。
-- 写入入口唯一：backend/src/services/securityEvent.service.js
CREATE TABLE IF NOT EXISTS security_events (
    id INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_fingerprint_time (fingerprint, last_seen_at),
    INDEX idx_event_time (event, created_at),
    INDEX idx_ip_time (ip, created_at),
    INDEX idx_target_time (target_user_id, last_seen_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='安全事件表（被拒的尝试，已聚合）';
