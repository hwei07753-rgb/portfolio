package com.example.zhixueban.entity.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UserStatsResponse {

    /**
     * 累计专注时长（分钟）
     */
    private Integer totalMinutes;

    /**
     * 累计打卡次数
     */
    private Integer totalCheckins;

    /**
     * 社区发帖总数
     */
    private Integer totalPosts;
}
