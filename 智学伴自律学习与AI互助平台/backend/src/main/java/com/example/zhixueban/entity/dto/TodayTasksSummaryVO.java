package com.example.zhixueban.entity.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TodayTasksSummaryVO {
    private String activePlanTitle;
    private Integer daysRemaining;
    private Integer progressPercent;
    private Integer completedCount;
    private Integer totalCount;
    private Integer earnedCoinsToday;
    private List<StudyTaskVO> tasks;
}
