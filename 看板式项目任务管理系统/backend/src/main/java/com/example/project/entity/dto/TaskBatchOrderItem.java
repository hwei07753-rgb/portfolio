package com.example.project.entity.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class TaskBatchOrderItem {

    @NotNull(message = "任务ID不能为空")
    private Long taskId;

    @NotNull(message = "排序号不能为空")
    private Integer orderNo;

    @NotBlank(message = "状态不能为空")
    private String status;
}