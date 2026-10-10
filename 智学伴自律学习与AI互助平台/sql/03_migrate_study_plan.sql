-- ============================================================
-- “智学伴”自律学习与互助平台 · 阶段性学业计划与每日任务清单 DDL
-- 版本：S2b / 2026-10-10
-- 说明：
--   1. study_plan 阶段性学习计划表（四六级/考研/期末/专业技能）
--   2. study_task 每日执行清单任务表（打勾完成、自律学分奖励、连续天数）
-- ============================================================

USE `zhixueban`;

-- ------------------------------------------------------------
-- 11. study_plan 阶段性学习计划表
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `study_task`;
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
-- 12. study_task 每日任务清单表
-- ------------------------------------------------------------
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

-- ------------------------------------------------------------
-- 为演示学员与所有现有用户注入默认【四级冲刺经典计划与任务】
-- ------------------------------------------------------------
INSERT INTO `study_plan` (`id`, `user_id`, `title`, `category`, `target_date`, `total_days`, `status`)
VALUES (1, 14, '大学英语四级(CET-4) 40天高分通关计划', '四六级', DATE_ADD(CURRENT_DATE, INTERVAL 38 DAY), 40, 0)
ON DUPLICATE KEY UPDATE `title` = VALUES(`title`);

INSERT INTO `study_task` (`plan_id`, `user_id`, `title`, `reward_coins`, `is_completed`, `continuous_days`)
VALUES 
(1, 14, '📖 在扇贝/百词斩背诵 50 个四级核心词汇', 5, 1, 3),
(1, 14, '🎧 完成 1 篇历年四级听力真题精听', 5, 0, 2),
(1, 14, '⏱️ 番茄钟沉浸专注阅读与真题训练 45 分钟', 5, 0, 1),
(1, 14, '📝 睡前整理今日错题并在智学伴打卡复盘', 5, 0, 3)
ON DUPLICATE KEY UPDATE `title` = VALUES(`title`);
