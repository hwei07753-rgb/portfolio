package com.example.zhixueban.entity.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class StudyPlanRequest {

    @NotBlank(message = "计划标题不能为空")
    private String title;

    private String category;

    private LocalDate targetDate;

    private Integer totalDays;

    private List<String> taskTitles;
}
