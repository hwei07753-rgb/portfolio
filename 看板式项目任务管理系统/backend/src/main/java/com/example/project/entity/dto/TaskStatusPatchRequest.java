package com.example.project.entity.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
public class TaskStatusPatchRequest {

    // R-05-issue-21: 已修复 - 添加@Pattern校验status/expectedStatus合法状态值(todo/in_progress/done/blocked/deleted),无效值在Controller层提前拒绝
    @NotBlank(message = "目标状态不能为空")
    @Pattern(regexp = "^(todo|in_progress|done|blocked|deleted)$", message = "无效的状态值")
    private String status;

    @NotBlank(message = "当前状态不能为空")
    @Pattern(regexp = "^(todo|in_progress|done|blocked|deleted)$", message = "无效的状态值")
    private String expectedStatus;

    /** P2: 阻塞原因（status=blocked 时必填 ≥10 字符） */
    @Size(min = 10, max = 1000, message = "阻塞原因至少10个字符")
    private String blockReason;

    /** P2: 客户端持有的乐观锁版本号 */
    private Integer version;
}