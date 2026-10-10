package com.example.zhixueban.entity.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class StudyPlanVO {
    private Long id;
    private Long userId;
    private String title;
    private String category;
    private LocalDate targetDate;
    private Integer totalDays;
    private Integer daysRemaining;
    private Integer status;
    private Integer progressPercent;
    private Integer completedTaskCount;
    private Integer totalTaskCount;
    private LocalDateTime createdAt;
    private List<StudyTaskVO> tasks;
}
