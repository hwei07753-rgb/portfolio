package com.example.zhixueban.entity.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 内容审核操作请求（通过/删除 + 原因）
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AuditRequest {

    /** 1=通过 2=删除 */
    @NotNull(message = "审核动作不能为空")
    @Min(value = 1, message = "审核动作取值 1=通过 2=删除")
    @Max(value = 2, message = "审核动作取值 1=通过 2=删除")
    private Integer status;

    /** 删除/驳回原因（可空） */
    @Size(max = 200, message = "原因长度不能超过 200")
    private String reason;
}
