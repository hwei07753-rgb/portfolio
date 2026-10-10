package com.example.project.entity.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.time.LocalDate;
import java.util.List;

@Data
public class TaskCreateRequest {

    @NotBlank(message = "请输入任务标题")
    @Size(max = 200, message = "标题不能超过200字符")
    private String title;

    @Size(max = 10000, message = "描述不能超过10000字符")
    private String description;

    // R-05-issue-6: 已修复 - 添加 @Pattern 校验 priority 为 low/medium/high/urgent 之一
    @Pattern(regexp = "^(low|medium|high|urgent)$", message = "优先级必须为 low/medium/high/urgent 之一")
    private String priority;

    private Long assigneeId;

    private LocalDate dueDate;

    private List<Long> labelIds;
}