package com.example.project.entity.dto;

import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.time.LocalDate;
import java.util.List;

@Data
public class TaskUpdateRequest {

    @Size(min = 1, max = 200, message = "标题1-200字符")
    private String title;

    @Size(max = 10000, message = "描述不能超过10000字符")
    private String description;

    // R-05-issue-7: 已修复 - 添加 @Pattern 校验 priority 为 low/medium/high/urgent 之一
    @Pattern(regexp = "^(low|medium|high|urgent)$", message = "优先级必须为 low/medium/high/urgent 之一")
    private String priority;

    private Long assigneeId;

    private LocalDate dueDate;

    // R-05-issue-7: 已修复 - 添加 @Pattern 校验 status 为 todo/in_progress/done/blocked/deleted 之一
    @Pattern(regexp = "^(todo|in_progress|done|blocked|deleted)$", message = "状态值非法")
    private String status;

    private String blockReason;

    private List<Long> labelIds;
}