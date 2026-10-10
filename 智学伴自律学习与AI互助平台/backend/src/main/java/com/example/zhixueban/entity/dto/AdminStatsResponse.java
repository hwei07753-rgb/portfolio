package com.example.zhixueban.entity.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 管理员后台：平台核心宏观指标
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AdminStatsResponse {

    /** 注册用户总数 */
    private Long userCount;

    /** 社区帖子总数（不含已删除） */
    private Long postCount;

    /** 每日打卡总数 */
    private Long checkinCount;

    /** 今日打卡数（SRS §3.2.4） */
    private Long todayCheckinCount;

    /** AI 调用次数（ai_review 表 COUNT，SRS §3.2.4） */
    private Long aiReviewCount;

    /** 平台专注总时长（分钟，仅统计完成记录） */
    private Integer focusTotalMinutes;
}
