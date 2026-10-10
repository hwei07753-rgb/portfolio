package com.example.project.entity.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotEmpty;
import lombok.Data;

import java.util.List;

@Data
public class TaskBatchOrderRequest {

    @NotEmpty(message = "排序列表不能为空")
    @Valid
    private List<TaskBatchOrderItem> items;
}