package com.example.zhixueban.entity.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

/**
 * 管理员后台：用户状态变更请求（0=正常 1=封禁）
 */
@Data
public class AdminUserStatusRequest {

    @NotNull(message = "状态不能为空")
    @Min(value = 0, message = "状态仅支持 0=正常 / 1=封禁")
    @Max(value = 1, message = "状态仅支持 0=正常 / 1=封禁")
    private Integer status;
}
