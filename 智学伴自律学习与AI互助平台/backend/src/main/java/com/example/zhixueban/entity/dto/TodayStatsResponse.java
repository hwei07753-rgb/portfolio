package com.example.zhixueban.entity.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 今日专注数据看板
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TodayStatsResponse {

    /** 今日专注总时长（分钟，仅统计完成记录） */
    private Integer todayMinutes;

    /** 今日专注次数（全部记录） */
    private Integer todayCount;

    /** 今日完成次数（status=0） */
    private Integer completedCount;
}
