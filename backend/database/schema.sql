-- ============================================================
-- 共创社区平台 数据库结构
-- 与 backend/src/models 中的 Sequelize 模型定义保持一致
-- ============================================================

CREATE DATABASE IF NOT EXISTS community_platform CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE community_platform;

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
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
