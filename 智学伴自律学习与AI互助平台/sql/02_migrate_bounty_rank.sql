-- ============================================================
-- “智学伴”自律学习与互助平台 · 学霸榜与悬赏答疑闭环数据库升级脚本
-- 版本：S2 / 2026-10-10
-- 说明：
--   1. user 表增加 coins 字段（自律积分/金币）
--   2. post 表增加 bounty_coins、is_solved、accepted_reply_id 字段
--   3. reply 表增加 is_accepted 字段
--   4. 建立索引提升学霸榜与统计查询性能
-- ============================================================

USE `zhixueban`;

-- 1. 用户表追加积分/金币
ALTER TABLE `user` ADD COLUMN `coins` INT NOT NULL DEFAULT 100 COMMENT '自律积分/金币';

-- 2. 社区帖子追加悬赏与结案字段
ALTER TABLE `post` ADD COLUMN `bounty_coins` INT NOT NULL DEFAULT 0 COMMENT '悬赏金币（0表示无悬赏）';
ALTER TABLE `post` ADD COLUMN `is_solved` TINYINT NOT NULL DEFAULT 0 COMMENT '是否已解决（0=未解决 1=已解决）';
ALTER TABLE `post` ADD COLUMN `accepted_reply_id` BIGINT NULL COMMENT '采纳的最佳回复ID';

-- 3. 回复表追加采纳标记
ALTER TABLE `reply` ADD COLUMN `is_accepted` TINYINT NOT NULL DEFAULT 0 COMMENT '是否被采纳为最佳答案（0=否 1=已采纳）';

-- 4. 优化榜单与统计查询索引
ALTER TABLE `focus_record` ADD INDEX `idx_user_status_time` (`user_id`, `status`, `start_time`);
ALTER TABLE `checkin` ADD INDEX `idx_user_status_created` (`user_id`, `status`, `created_at`);
