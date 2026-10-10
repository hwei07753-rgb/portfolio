package com.example.zhixueban.entity.dto;

import com.example.zhixueban.entity.StudyTask;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class StudyTaskVO {
    private Long id;
    private Long planId;
    private String planTitle;
    private String title;
    private Integer rewardCoins;
    private Integer isCompleted;
    private LocalDateTime completedAt;
    private Integer continuousDays;

    public static StudyTaskVO fromEntity(StudyTask task) {
        return StudyTaskVO.builder()
                .id(task.getId())
                .planId(task.getPlanId())
                .title(task.getTitle())
                .rewardCoins(task.getRewardCoins() != null ? task.getRewardCoins() : 5)
                .isCompleted(task.getIsCompleted() != null ? task.getIsCompleted() : 0)
                .completedAt(task.getCompletedAt())
                .continuousDays(task.getContinuousDays() != null ? task.getContinuousDays() : 0)
                .build();
    }
}
