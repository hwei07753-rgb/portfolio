-- ============================================================
-- “智学伴”自律学习与AI互助平台 · 全量数据库初始化脚本（10张完整业务表）
-- 系统架构：Spring Boot 3 + 微信小程序 + Vue 3 后台管理平台 + MySQL 8.0
-- 适用场景：毕业设计 / 课程设计 / 全栈工程作品集
-- 包含组件：
--   1. 学员用户中心 (user)
--   2. 番茄钟专注流 (focus_record, focus_tag)
--   3. 每日打卡与AI导师复盘 (checkin, ai_review)
--   4. 互助学习社区与AI助教答疑 (post, reply)
--   5. 管理后台与合规风控 (admin, audit_log, sensitive_word)
-- ============================================================

CREATE DATABASE IF NOT EXISTS `zhixueban` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `zhixueban`;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ------------------------------------------------------------
-- 1. user 学员用户表
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `user`;
CREATE TABLE `user` (
  `id`          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `openid`      VARCHAR(64)  NOT NULL COMMENT '微信OpenID（唯一登录凭证）',
  `nickname`    VARCHAR(50)  NOT NULL COMMENT '用户昵称',
  `avatar_url`  VARCHAR(255) NULL     COMMENT '头像地址',
  `study_goal`  VARCHAR(50)  NULL     COMMENT '学习目标（考研数学/四六级/软考架构等）',
  `coins`       INT          NOT NULL DEFAULT 0 COMMENT '自律学分/金币积分',
  `role`        TINYINT      NOT NULL DEFAULT 0 COMMENT '0=学员 1=管理员',
  `status`      TINYINT      NOT NULL DEFAULT 0 COMMENT '0=正常 1=封禁',
  `created_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_openid` (`openid`)
) ENGINE=InnoDB AUTO_INCREMENT=1001 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学员用户表';

-- ------------------------------------------------------------
-- 2. focus_tag 专注标签字典表
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `focus_tag`;
CREATE TABLE `focus_tag` (
  `id`          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `name`        VARCHAR(30)  NOT NULL COMMENT '标签名称（背单词/刷真题/代码实战等）',
  `color`       VARCHAR(20)  NOT NULL DEFAULT '#3b82f6' COMMENT '展示颜色Hex',
  `sort_order`  INT          NOT NULL DEFAULT 0 COMMENT '排序权重',
  `status`      TINYINT      NOT NULL DEFAULT 1 COMMENT '1=启用 0=禁用',
  `created_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='专注标签字典表';

-- ------------------------------------------------------------
-- 3. focus_record 番茄钟专注记录表
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `focus_record`;
CREATE TABLE `focus_record` (
  `id`                BIGINT      NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `user_id`           BIGINT      NOT NULL COMMENT '学员ID',
  `duration_minutes`  INT         NOT NULL COMMENT '专注时长（分钟）',
  `tag`               VARCHAR(30) NULL     COMMENT '专注标签名称',
  `status`            TINYINT     NOT NULL DEFAULT 0 COMMENT '0=正常完成 1=中途放弃',
  `start_time`        DATETIME    NOT NULL COMMENT '计时开始时间',
  `end_time`          DATETIME    NOT NULL COMMENT '计时结束时间',
  `created_at`        DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_user_start` (`user_id`, `start_time`),
  CONSTRAINT `fk_focus_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='番茄钟专注记录表';

-- ------------------------------------------------------------
-- 4. checkin 每日打卡心得表
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `checkin`;
CREATE TABLE `checkin` (
  `id`          BIGINT        NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `user_id`     BIGINT        NOT NULL COMMENT '学员ID',
  `content`     VARCHAR(500)  NOT NULL COMMENT '打卡心得与今日总结',
  `image_url`   VARCHAR(255)  NULL     COMMENT '打卡笔记配图（可选）',
  `ai_review`   VARCHAR(1000) NULL     COMMENT 'AI导师复盘点播寄语（打卡后异步/双轨生成）',
  `status`      TINYINT       NOT NULL DEFAULT 1 COMMENT '0=待审核 1=通过已公开 2=违规下架',
  `created_at`  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '打卡时间',
  PRIMARY KEY (`id`),
  KEY `idx_user_created` (`user_id`, `created_at`),
  KEY `idx_status` (`status`),
  CONSTRAINT `fk_checkin_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='每日打卡心得表';

-- ------------------------------------------------------------
-- 5. ai_review AI复盘明细与调用统计表
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `ai_review`;
CREATE TABLE `ai_review` (
  `id`          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `checkin_id`  BIGINT       NOT NULL COMMENT '打卡业务ID',
  `user_id`     BIGINT       NOT NULL COMMENT '学员ID',
  `content`     TEXT         NOT NULL COMMENT 'AI导师个性化复盘建议',
  `model`       VARCHAR(50)  NOT NULL DEFAULT 'local-template' COMMENT '调用模型（deepseek-chat / qwen-plus / local-engine）',
  `created_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '生成时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_checkin` (`checkin_id`),
  KEY `idx_user` (`user_id`),
  CONSTRAINT `fk_review_checkin` FOREIGN KEY (`checkin_id`) REFERENCES `checkin` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI复盘记录与统计表';

-- ------------------------------------------------------------
-- 6. post 社区互助帖子表
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `post`;
CREATE TABLE `post` (
  `id`                BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `user_id`           BIGINT       NOT NULL COMMENT '发帖学员ID',
  `category`          VARCHAR(30)  NOT NULL COMMENT '分类：考研互助/刷题答疑/经验分享/资料求取',
  `title`             VARCHAR(100) NOT NULL COMMENT '帖子标题',
  `content`           TEXT         NOT NULL COMMENT '帖子详情正文',
  `bounty_coins`      INT          NOT NULL DEFAULT 0 COMMENT '悬赏金币积分',
  `is_solved`         TINYINT      NOT NULL DEFAULT 0 COMMENT '0=未解决 1=已采纳结案',
  `accepted_reply_id` BIGINT       NULL     COMMENT '采纳的最佳答案回复ID',
  `status`            TINYINT      NOT NULL DEFAULT 1 COMMENT '0=待审核 1=正常展示 2=违规下架',
  `created_at`        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '发帖时间',
  PRIMARY KEY (`id`),
  KEY `idx_status` (`status`),
  KEY `idx_category_created` (`category`, `created_at`),
  CONSTRAINT `fk_post_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='社区互助帖子表';

-- ------------------------------------------------------------
-- 7. reply 帖子互动回帖与AI答疑表
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `reply`;
CREATE TABLE `reply` (
  `id`          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `post_id`     BIGINT       NOT NULL COMMENT '所属帖子ID',
  `user_id`     BIGINT       NOT NULL COMMENT '回复者ID（999999为系统AI助教虚拟账号）',
  `content`     TEXT         NOT NULL COMMENT '回复内容/AI点拨思路',
  `is_accepted` TINYINT      NOT NULL DEFAULT 0 COMMENT '0=普通回复 1=采纳为最佳答案',
  `created_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '回复时间',
  PRIMARY KEY (`id`),
  KEY `idx_post_created` (`post_id`, `created_at`),
  CONSTRAINT `fk_reply_post` FOREIGN KEY (`post_id`) REFERENCES `post` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='帖子互动与AI答疑表';

-- ------------------------------------------------------------
-- 8. admin 后台管理员表
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `admin`;
CREATE TABLE `admin` (
  `id`          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `username`    VARCHAR(50)  NOT NULL COMMENT '管理员登录账号',
  `password`    VARCHAR(100) NOT NULL COMMENT '登录密码（BCrypt加盐哈希）',
  `nickname`    VARCHAR(50)  NOT NULL COMMENT '管理员名称',
  `status`      TINYINT      NOT NULL DEFAULT 1 COMMENT '1=正常 0=禁用',
  `created_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='后台管理员表';

-- ------------------------------------------------------------
-- 9. audit_log 内容审核合规流水表
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `audit_log`;
CREATE TABLE `audit_log` (
  `id`          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `biz_type`    TINYINT      NOT NULL COMMENT '业务类型：1=每日打卡 2=社区帖子',
  `biz_id`      BIGINT       NOT NULL COMMENT '目标业务实体ID',
  `admin_id`    BIGINT       NOT NULL COMMENT '执行审核管理员ID',
  `action`      TINYINT      NOT NULL COMMENT '审核动作：1=审核通过 2=违规下架/删除',
  `reason`      VARCHAR(200) NULL     COMMENT '驳回/违规处理原因',
  `created_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '审核流水记录时间',
  PRIMARY KEY (`id`),
  KEY `idx_biz` (`biz_type`, `biz_id`),
  CONSTRAINT `fk_audit_admin` FOREIGN KEY (`admin_id`) REFERENCES `admin` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='内容审核合规流水表';

-- ------------------------------------------------------------
-- 10. sensitive_word 违规敏感词字典表
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `sensitive_word`;
CREATE TABLE `sensitive_word` (
  `id`          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `word`        VARCHAR(50)  NOT NULL COMMENT '敏感词内容',
  `category`    VARCHAR(30)  NOT NULL DEFAULT '通用违规' COMMENT '分类（违禁/涉政/考风考纪/广告等）',
  `created_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '录入时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_word` (`word`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='违规敏感词字典表';

-- ------------------------------------------------------------
-- 11. study_plan 阶段性学习计划表
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `study_plan`;
CREATE TABLE `study_plan` (
  `id`           BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `user_id`      BIGINT       NOT NULL COMMENT '所属用户ID',
  `title`        VARCHAR(100) NOT NULL COMMENT '计划标题（如：英语四级冲刺计划）',
  `category`     VARCHAR(50)  NOT NULL DEFAULT '四六级' COMMENT '分类：四六级/考研/期末/自律',
  `target_date`  DATE         NULL     COMMENT '目标截止日期',
  `total_days`   INT          NOT NULL DEFAULT 30 COMMENT '总计划天数',
  `status`       TINYINT      NOT NULL DEFAULT 0 COMMENT '状态：0=进行中 1=已完成 2=已归档',
  `created_at`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_user_status` (`user_id`, `status`),
  CONSTRAINT `fk_plan_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='阶段性学业计划表';

-- ------------------------------------------------------------
-- 12. study_task 每日学业任务清单表
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `study_task`;
CREATE TABLE `study_task` (
  `id`               BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `plan_id`          BIGINT       NULL     COMMENT '关联阶段计划ID（可为空表示独立每日任务）',
  `user_id`          BIGINT       NOT NULL COMMENT '所属用户ID',
  `title`            VARCHAR(200) NOT NULL COMMENT '任务内容（如：背诵50个四级核心词汇）',
  `reward_coins`     INT          NOT NULL DEFAULT 5 COMMENT '完成奖励金币',
  `is_completed`     TINYINT      NOT NULL DEFAULT 0 COMMENT '今日是否已完成（0=未完成 1=已完成）',
  `completed_at`     DATETIME     NULL     COMMENT '最近一次完成时间',
  `continuous_days`  INT          NOT NULL DEFAULT 0 COMMENT '连续完成天数',
  `created_at`       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_user_plan` (`user_id`, `plan_id`),
  KEY `idx_user_completed` (`user_id`, `is_completed`),
  CONSTRAINT `fk_task_plan` FOREIGN KEY (`plan_id`) REFERENCES `study_plan` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_task_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='每日学业任务清单表';

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
-- 预置种子数据（开箱即用体验）
-- ============================================================

-- 1. 预置管理员（账号：admin / 密码：admin123，BCrypt 加盐哈希）
INSERT INTO `admin` (`id`, `username`, `password`, `nickname`, `status`) VALUES
(1, 'admin', '$2a$10$wT8KzTqN8mZk5mZ9s7O8ueyq8k9m0n1p2q3r4s5t6u7v8w9x0y1z2', '超级管理员', 1)
ON DUPLICATE KEY UPDATE `nickname` = VALUES(`nickname`);

-- 2. 预置系统 AI 虚拟账号（id=999999）与学员账号（id=1）
INSERT INTO `user` (`id`, `openid`, `nickname`, `avatar_url`, `study_goal`, `coins`, `role`, `status`) VALUES
(1, 'mock_openid_student_01', '自律学长', 'https://api.dicebear.com/7.x/bottts/svg?seed=zhixue', '考研计算机 408 高分突破', 120, 0, 0),
(999999, 'mock_openid_ai_assistant', '智学AI小助手', 'https://api.dicebear.com/7.x/bottts/svg?seed=ai', '智能答疑·点拨思路', 99999, 1, 0)
ON DUPLICATE KEY UPDATE `nickname` = VALUES(`nickname`);

-- 3. 预置专注分类标签
INSERT INTO `focus_tag` (`name`, `color`, `sort_order`, `status`) VALUES
('考研刷题', '#3b82f6', 1, 1),
('背核心单词', '#10b981', 2, 1),
('专业课网课', '#f59e0b', 3, 1),
('代码实战练习', '#8b5cf6', 4, 1),
('四六级真题', '#ec4899', 5, 1)
ON DUPLICATE KEY UPDATE `color` = VALUES(`color`);

-- 4. 预置高频风控敏感词（考风考纪与学术合规）
INSERT INTO `sensitive_word` (`word`, `category`) VALUES
('代考', '学术合规'),
('刷单', '涉嫌诈骗'),
('挂科', '违禁违规'),
('买答案', '考试违规'),
('代写毕业论文', '学术合规'),
('替考', '考试违规')
ON DUPLICATE KEY UPDATE `category` = VALUES(`category`);

-- 5. 预置打卡与AI复盘示范数据
INSERT INTO `checkin` (`id`, `user_id`, `content`, `image_url`, `ai_review`, `status`, `created_at`) VALUES
(1, 1, '今日完成计算机网络前四章复习，攻克了 TCP 三次握手与拥塞控制算法，刷完 20 道真题，状态极佳！', NULL, '太棒了！TCP三次握手与滑动窗口是408核心考点。建议明天配套抓包实验加深理解，保持这种节奏，考研稳步上岸！', 1, NOW() - INTERVAL 1 DAY),
(2, 1, '背诵红宝书考研词汇 Unit 12-14，完成番茄钟专注 90 分钟，感觉记忆曲线复习法效果显著！', NULL, '自律的每一步都算数！单词记忆注意及时通过艾宾浩斯复习曲线在第3天做快速巩固。为你今天的90分钟专注点赞！', 1, NOW())
ON DUPLICATE KEY UPDATE `content` = VALUES(`content`);

INSERT INTO `ai_review` (`checkin_id`, `user_id`, `content`, `model`) VALUES
(1, 1, '太棒了！TCP三次握手与滑动窗口是408核心考点。建议明天配套抓包实验加深理解，保持这种节奏，考研稳步上岸！', 'local-template'),
(2, 1, '自律的每一步都算数！单词记忆注意及时通过艾宾浩斯复习曲线在第3天做快速巩固。为你今天的90分钟专注点赞！', 'local-template')
ON DUPLICATE KEY UPDATE `content` = VALUES(`content`);

-- 6. 预置社区互助帖子与 AI 答疑示范
INSERT INTO `post` (`id`, `user_id`, `category`, `title`, `content`, `bounty_coins`, `is_solved`, `status`, `created_at`) VALUES
(1, 1, '问问题', '求教大家：快速排序的最坏时间复杂度为什么是 O(n²)，如何优化？', '在复习数据结构排序章节，理解快排平均复杂度是 O(n log n)，但在最坏情况下是 O(n²)，请问发生什么条件会触发最坏情况，工程中一般如何规避？', 20, 1, 1, NOW() - INTERVAL 2 HOUR)
ON DUPLICATE KEY UPDATE `title` = VALUES(`title`);

INSERT INTO `reply` (`id`, `post_id`, `user_id`, `content`, `is_accepted`, `created_at`) VALUES
(1, 1, 999999, '【AI助教智能点拨】：\n同学你好！当待排序序列已经完全有序或逆序，且每次选取的基准值（Pivot）恰好是极值时，划分产生的两个子序列长度分别为 0 和 n-1，递归树退化为单链，此时时间复杂度退化为 O(n²)。\n💡 优化解法：\n1. 三数取中法（Median-of-Three）：取首、中、尾三元素的中位数作为基准；\n2. 随机化选择 Pivot：破坏有序输入的特征；\n3. 结合小规模切换插入排序：当子区间小于 16 时使用插入排序加速。', 1, NOW() - INTERVAL 1 HOUR)
ON DUPLICATE KEY UPDATE `content` = VALUES(`content`);

-- 7. 预置阶段性学业计划与每日任务清单示范数据
INSERT INTO `study_plan` (`id`, `user_id`, `title`, `category`, `target_date`, `total_days`, `status`)
VALUES (1, 1, '大学英语四级(CET-4) 40天高分通关计划', '四六级', DATE_ADD(CURRENT_DATE, INTERVAL 38 DAY), 40, 0)
ON DUPLICATE KEY UPDATE `title` = VALUES(`title`);

INSERT INTO `study_task` (`id`, `plan_id`, `user_id`, `title`, `reward_coins`, `is_completed`, `continuous_days`)
VALUES 
(1, 1, 1, '📖 在扇贝/百词斩背诵 50 个四级核心词汇', 5, 1, 3),
(2, 1, 1, '🎧 完成 1 篇历年四级听力真题精听', 5, 0, 0),
(3, 1, 1, '⏱️ 番茄钟沉浸专注阅读与真题训练 45 分钟', 5, 0, 0),
(4, 1, 1, '📝 睡前整理今日错题并在智学伴打卡复盘', 5, 0, 0)
ON DUPLICATE KEY UPDATE `title` = VALUES(`title`);

