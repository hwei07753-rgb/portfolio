package com.example.zhixueban.entity.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class StudyTaskRequest {

    private Long planId;

    @NotBlank(message = "任务内容不能为空")
    private String title;

    private Integer rewardCoins;
}
