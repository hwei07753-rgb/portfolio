-- ============================================================
-- “智学伴”自律学习与互助平台 · 数据库初始化脚本
-- 版本：S1 / 2026-09-30
-- 依据：SRS V2.0 §5 + docs/DATABASE_DESIGN.md（5 张表）
-- 环境：MySQL 8.0+，字符集 utf8mb4
-- 用法：mysql -u root -p < init_schema.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS `zhixueban` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `zhixueban`;

-- ------------------------------------------------------------
-- 1. user 用户表
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `user`;
CREATE TABLE `user` (
  `id`          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `openid`      VARCHAR(64)  NOT NULL COMMENT '微信OpenID（登录凭证）',
  `nickname`    VARCHAR(50)  NOT NULL COMMENT '昵称',
  `avatar_url`  VARCHAR(255) NULL     COMMENT '头像地址',
  `study_goal`  VARCHAR(50)  NULL     COMMENT '学习目标方向（考研/四六级）',
  `role`        TINYINT      NOT NULL DEFAULT 0 COMMENT '0=学员 1=管理员',
  `status`      TINYINT      NOT NULL DEFAULT 0 COMMENT '0=正常 1=封禁',
  `created_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_openid` (`openid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- ------------------------------------------------------------
-- 2. focus_record 专注记录表
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `focus_record`;
CREATE TABLE `focus_record` (
  `id`                BIGINT      NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `user_id`           BIGINT      NOT NULL COMMENT '用户ID',
  `duration_minutes`  INT         NOT NULL COMMENT '专注时长（分钟）',
  `tag`               VARCHAR(20) NULL     COMMENT '专注标签（背单词/刷题/看网课）',
  `status`            TINYINT     NOT NULL DEFAULT 0 COMMENT '0=完成 1=放弃',
  `start_time`        DATETIME    NOT NULL COMMENT '开始时间',
  `end_time`          DATETIME    NOT NULL COMMENT '结束时间',
  PRIMARY KEY (`id`),
  KEY `idx_user_start` (`user_id`, `start_time`),
  CONSTRAINT `fk_focus_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='专注记录表';

-- ------------------------------------------------------------
-- 3. checkin 每日打卡表
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `checkin`;
CREATE TABLE `checkin` (
  `id`          BIGINT        NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `user_id`     BIGINT        NOT NULL COMMENT '用户ID',
  `content`     VARCHAR(500)  NOT NULL COMMENT '打卡心得',
  `image_url`   VARCHAR(255)  NULL     COMMENT '配图（可空）',
  `ai_review`   VARCHAR(1000) NULL     COMMENT 'AI复盘建议（打卡后生成）',
  `status`      TINYINT       NOT NULL DEFAULT 0 COMMENT '0=待审核 1=通过 2=删除',
  `created_at`  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_user_created` (`user_id`, `created_at`),
  KEY `idx_status` (`status`),
  CONSTRAINT `fk_checkin_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='每日打卡表';

-- ------------------------------------------------------------
-- 4. post 社区帖子表
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `post`;
CREATE TABLE `post` (
  `id`          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `user_id`     BIGINT       NOT NULL COMMENT '发帖用户ID',
  `category`    VARCHAR(20)  NOT NULL COMMENT '分类：求资料/问问题/经验分享',
  `title`       VARCHAR(100) NOT NULL COMMENT '标题',
  `content`     TEXT         NOT NULL COMMENT '内容',
  `status`      TINYINT      NOT NULL DEFAULT 0 COMMENT '0=待审核 1=通过 2=删除',
  `created_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_status` (`status`),
  KEY `idx_category_created` (`category`, `created_at`),
  CONSTRAINT `fk_post_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='社区帖子表';

-- ------------------------------------------------------------
-- 5. reply 回复表
-- ------------------------------------------------------------
DROP TABLE IF EXISTS `reply`;
CREATE TABLE `reply` (
  `id`          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `post_id`     BIGINT       NOT NULL COMMENT '帖子ID',
  `user_id`     BIGINT       NOT NULL COMMENT '回复用户ID',
  `content`     VARCHAR(500) NOT NULL COMMENT '回复内容',
  `created_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_post_created` (`post_id`, `created_at`),
  CONSTRAINT `fk_reply_post` FOREIGN KEY (`post_id`) REFERENCES `post` (`id`),
  CONSTRAINT `fk_reply_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='回复表';

-- ============================================================
-- 测试数据（数据为验证：供 S2 后端联调使用）
-- 说明：openid 为演示值，正式接入微信后由 wx.login 换取
-- ============================================================

-- 管理员 + 学员
INSERT INTO `user` (`openid`, `nickname`, `study_goal`, `role`, `status`) VALUES
('admin_openid_0001', '系统管理员', NULL, 1, 0),
('demo_openid_0001', '张三', '考研', 0, 0),
('demo_openid_0002', '李四', '四六级', 0, 0);

-- 专注记录（张三今日已完成2个番茄钟）
INSERT INTO `focus_record` (`user_id`, `duration_minutes`, `tag`, `status`, `start_time`, `end_time`) VALUES
(2, 25, '背单词', 0, DATE_SUB(NOW(), INTERVAL 3 HOUR), DATE_SUB(NOW(), INTERVAL 155 MINUTE)),
(2, 25, '刷题',   0, DATE_SUB(NOW(), INTERVAL 2 HOUR), DATE_SUB(NOW(), INTERVAL 95 MINUTE));

-- 打卡记录（张三 1 条已通过、1 条待审核）
INSERT INTO `checkin` (`user_id`, `content`, `image_url`, `ai_review`, `status`) VALUES
(2, '今天背了 50 个单词，做了 2 套阅读，感觉状态不错！', NULL, '坚持就是胜利！明天建议增加 20 分钟作文练习，保持节奏。', 1),
(3, '完成四六级真题听力一套，错 6 个，继续加油。', NULL, NULL, 0);

-- 社区帖子（2 条通过 + 1 条待审核）
INSERT INTO `post` (`user_id`, `category`, `title`, `content`, `status`) VALUES
(2, '经验分享', '考研英语一 80 分经验贴', '单词坚持用 APP 打卡，真题精读三遍，作文背模板+练字。', 1),
(3, '求资料', '求四六级听力真题 PDF', '哪位同学有四六级近五年听力真题，求分享，谢谢！', 1),
(2, '问问题', '高数中值定理怎么学', '感觉中值定理证明题无从下手，求大佬指点方法。', 0);

-- 回复（帖子1 有 1 条回复）
INSERT INTO `reply` (`post_id`, `user_id`, `content`) VALUES
(1, 3, '感谢分享，单词打卡这个方法很实用！');
