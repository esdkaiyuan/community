-- ========================================
-- 共创社区平台 - 数据库初始化脚本
-- ========================================

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS co_creation_dev 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

-- 使用数据库
USE co_creation_dev;

-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) NOT NULL UNIQUE,
  email VARCHAR(100) NOT NULL UNIQUE,
  password VARCHAR(255) NOT NULL,
  avatar VARCHAR(255) DEFAULT NULL,
  bio TEXT DEFAULT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_username (username),
  INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建分类表
CREATE TABLE IF NOT EXISTS categories (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(50) NOT NULL,
  description TEXT DEFAULT NULL,
  icon VARCHAR(50) DEFAULT NULL,
  sort_order INT DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_sort_order (sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建项目表
CREATE TABLE IF NOT EXISTS projects (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  category_id INT NOT NULL,
  title VARCHAR(200) NOT NULL,
  description TEXT DEFAULT NULL,
  cover_image VARCHAR(255) DEFAULT NULL,
  tags JSON DEFAULT NULL,
  status ENUM('draft', 'published', 'archived') DEFAULT 'published',
  views INT DEFAULT 0,
  likes INT DEFAULT 0,
  participants INT DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
  INDEX idx_user_id (user_id),
  INDEX idx_category_id (category_id),
  INDEX idx_status (status),
  INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建点赞表
CREATE TABLE IF NOT EXISTS project_likes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  project_id INT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY unique_user_project (user_id, project_id),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
  INDEX idx_project_id (project_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建参与表
CREATE TABLE IF NOT EXISTS project_participants (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  project_id INT NOT NULL,
  status ENUM('pending', 'accepted', 'rejected') DEFAULT 'pending',
  message TEXT DEFAULT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY unique_user_project (user_id, project_id),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
  INDEX idx_project_id (project_id),
  INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建评论表
CREATE TABLE IF NOT EXISTS comments (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  project_id INT NOT NULL,
  parent_id INT DEFAULT NULL,
  content TEXT NOT NULL,
  likes INT DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
  FOREIGN KEY (parent_id) REFERENCES comments(id) ON DELETE CASCADE,
  INDEX idx_project_id (project_id),
  INDEX idx_parent_id (parent_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 插入种子数据
-- ========================================

-- 插入分类数据
INSERT INTO categories (name, description, icon, sort_order) VALUES
('技术开发', '编程、软件、算法等技术类项目', 'Monitor', 1),
('设计创意', 'UI/UX、平面设计、插画等设计项目', 'Picture', 2),
('教育学习', '课程、教程、知识分享等教育项目', 'Reading', 3),
('商业创业', '商业模式、创业项目、投资等', 'Briefcase', 4),
('生活兴趣', '美食、旅行、摄影等生活类项目', 'CoffeeCup', 5),
('游戏娱乐', '游戏开发、电竞、娱乐内容', 'VideoPlay', 6),
('科学研究', '学术研究、科学实验、数据分析', 'Microscope', 7),
('社会公益', '志愿服务、公益活动、慈善项目', 'Handset', 8)
ON DUPLICATE KEY UPDATE name=name;

-- 插入测试用户
INSERT INTO users (username, email, password, avatar, bio) VALUES
('test_admin', 'admin@example.com', '$2b$10$YourHashedPasswordHere', '/avatars/admin.jpg', '平台管理员'),
('developer_zhang', 'zhang@example.com', '$2b$10$YourHashedPasswordHere', '/avatars/zhang.jpg', '全栈开发工程师，热爱开源'),
('designer_li', 'li@example.com', '$2b$10$YourHashedPasswordHere', '/avatars/li.jpg', 'UI/UX 设计师，追求极致体验'),
('student_wang', 'wang@example.com', '$2b$10$YourHashedPasswordHere', '/avatars/wang.jpg', '计算机科学专业学生')
ON DUPLICATE KEY UPDATE username=username;

-- 插入测试项目
INSERT INTO projects (user_id, category_id, title, description, cover_image, tags, status, views, likes, participants) VALUES
(2, 1, 'AI 智能助手系统', '基于大语言模型的智能助手，支持多轮对话、任务规划和知识检索', '/covers/ai-assistant.jpg', '["AI", "Python", "NLP"]', 'published', 1250, 89, 23),
(3, 2, '现代化设计系统', '一套完整的企业级设计系统，包含组件库、图标库和设计规范', '/covers/design-system.jpg', '["UI", "Design", "Figma"]', 'published', 890, 67, 15),
(4, 3, '编程入门教程', '从零开始学习编程，涵盖 HTML、CSS、JavaScript 基础', '/covers/coding-tutorial.jpg', '["Tutorial", "Web", "Beginner"]', 'published', 2340, 156, 45),
(2, 1, '区块链技术平台', '去中心化应用开发平台，支持智能合约部署和调用', '/covers/blockchain.jpg', '["Blockchain", "Solidity", "Web3"]', 'published', 670, 45, 12),
(3, 2, '移动端 App 设计', '一款健康管理 App 的完整设计方案，包含交互原型', '/covers/mobile-app.jpg', '["Mobile", "Health", "Prototype"]', 'published', 560, 38, 8)
ON DUPLICATE KEY UPDATE title=title;

-- ========================================
-- 验证数据
-- ========================================

SELECT '数据库初始化完成！' AS message;
SELECT COUNT(*) AS category_count FROM categories;
SELECT COUNT(*) AS user_count FROM users;
SELECT COUNT(*) AS project_count FROM projects;
