package com.example.project.entity.dto;

import jakarta.validation.constraints.Pattern;
import lombok.Data;

/** 甘特图拖拽时间条 → 更新截止日期 */
@Data
public class TaskDueDateRequest {

    /** 截止日期 ISO 8601 日期格式，可设为 null 清除截止日期 */
    @Pattern(regexp = "^(\\d{4}-\\d{2}-\\d{2})?$", message = "日期格式不正确")
    private String dueDate;
}
