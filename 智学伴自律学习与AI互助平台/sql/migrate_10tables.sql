-- ============================================================
-- “智学伴”自律学习与互助平台 · 数据库扩表脚本（5 表 → 10 表）
-- 版本：S1b / 2026-10-09
-- 依据：SRS V2.0 §3/§5/§6.2（管理员登录、内容审核、AI复盘、敏感词过滤、专注标签）
-- 说明：在现有 5 张核心表基础上新增 5 张表，并将 checkin.ai_review 拆分为独立 ai_review 表
-- 环境：MySQL 8.0+，字符集 utf8mb4
-- 用法：mysql -u root -p < migrate_10tables.sql（需在已初始化 5 表库上执行）
-- ============================================================

USE `zhixueban`;

-- ------------------------------------------------------------
-- 6. admin 管理员表（SRS 3.2.1 预设管理员账号密码登录后台）
-- 说明：管理员账号独立于微信用户表；密码 BCrypt 加密，初始账号由后端启动时初始化
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `admin`;
CREATE TABLE `admin` (
  `id`          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `username`    VARCHAR(50)  NOT NULL COMMENT '登录账号',
  `password`    VARCHAR(100) NOT NULL COMMENT '密码（BCrypt加密）',
  `nickname`    VARCHAR(50)  NOT NULL COMMENT '管理员昵称',
  `status`      TINYINT      NOT NULL DEFAULT 1 COMMENT '1=正常 0=禁用',
  `created_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='后台管理员表';

-- ------------------------------------------------------------
-- 7. audit_log 审核记录表（SRS 3.2.3 内容审核留痕）
-- 说明：打卡/帖子“通过/删除”操作记录，可追溯审核历史
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `audit_log`;
CREATE TABLE `audit_log` (
  `id`          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `biz_type`    TINYINT      NOT NULL COMMENT '审核对象类型 1=打卡 2=帖子',
  `biz_id`      BIGINT       NOT NULL COMMENT '业务ID（打卡ID/帖子ID）',
  `admin_id`    BIGINT       NOT NULL COMMENT '操作管理员ID',
  `action`      TINYINT      NOT NULL COMMENT '审核动作 1=通过 2=删除',
  `reason`      VARCHAR(200) NULL     COMMENT '删除/驳回原因',
  `created_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '审核时间',
  PRIMARY KEY (`id`),
  KEY `idx_biz` (`biz_type`, `biz_id`),
  CONSTRAINT `fk_audit_admin` FOREIGN KEY (`admin_id`) REFERENCES `admin` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='内容审核记录表';

-- ------------------------------------------------------------
-- 8. ai_review AI复盘表（SRS 3.1.3 AI建议 + 3.2.4 AI调用次数统计）
-- 说明：打卡的 AI 复盘建议独立成表（1:1），便于统计 AI 调用次数
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `ai_review`;
CREATE TABLE `ai_review` (
  `id`          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `checkin_id`  BIGINT       NOT NULL COMMENT '打卡ID',
  `user_id`     BIGINT       NOT NULL COMMENT '用户ID',
  `content`     TEXT         NOT NULL COMMENT 'AI复盘建议内容',
  `model`       VARCHAR(50)  NOT NULL DEFAULT 'local-template' COMMENT '生成模型（deepseek/通义/local-template）',
  `created_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '生成时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_checkin` (`checkin_id`),
  KEY `idx_user` (`user_id`),
  CONSTRAINT `fk_ai_checkin` FOREIGN KEY (`checkin_id`) REFERENCES `checkin` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI复盘表';

-- ------------------------------------------------------------
-- 9. sensitive_word 敏感词表（SRS 6.2.2 简单敏感词过滤）
-- 说明：发帖/打卡内容命中启用中的敏感词时拒绝提交
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `sensitive_word`;
CREATE TABLE `sensitive_word` (
  `id`          BIGINT      NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `word`        VARCHAR(50) NOT NULL COMMENT '敏感词',
  `status`      TINYINT     NOT NULL DEFAULT 1 COMMENT '1=启用 0=停用',
  `created_at`  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_word` (`word`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='敏感词表';

-- ------------------------------------------------------------
-- 10. focus_tag 专注标签字典表（SRS 3.1.2 番茄钟专注标签规范化）
-- 说明：番茄钟标签从自由文本规范为字典选择，与 focus_record.tag 对应
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `focus_tag`;
CREATE TABLE `focus_tag` (
  `id`          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `name`        VARCHAR(20)  NOT NULL COMMENT '标签名（背单词/刷题/看网课/编程/阅读/其他）',
  `icon`        VARCHAR(50)  NULL     COMMENT '图标（emoji）',
  `sort`        INT          NOT NULL DEFAULT 0 COMMENT '排序值（小在前）',
  `status`      TINYINT      NOT NULL DEFAULT 1 COMMENT '1=启用 0=停用',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='专注标签字典表';

-- ------------------------------------------------------------
-- 数据迁移：checkin.ai_review → ai_review 表（1:1，不丢历史数据）
-- ------------------------------------------------------------
INSERT INTO `ai_review` (`checkin_id`, `user_id`, `content`, `model`)
SELECT `id`, `user_id`, `ai_review`, 'local-template'
FROM `checkin`
WHERE `ai_review` IS NOT NULL AND `ai_review` <> '';

ALTER TABLE `checkin` DROP COLUMN `ai_review`;

-- ------------------------------------------------------------
-- 种子数据
-- ------------------------------------------------------------

-- 专注标签字典（SRS 3.1.2）
INSERT INTO `focus_tag` (`name`, `icon`, `sort`) VALUES
('背单词', '📖', 1),
('刷题',   '✏️', 2),
('看网课', '🎬', 3),
('编程',   '💻', 4),
('阅读',   '📚', 5),
('其他',   '🌟', 6);

-- 敏感词样例（SRS 6.2.2，演示用）
INSERT INTO `sensitive_word` (`word`, `status`) VALUES
('代考', 1),
('作弊', 1),
('代写', 1),
('刷单', 1);
