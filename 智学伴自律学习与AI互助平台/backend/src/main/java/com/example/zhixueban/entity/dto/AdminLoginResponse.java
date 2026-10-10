package com.example.zhixueban.entity.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 后台管理员登录响应（JWT + 管理员基本信息）
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AdminLoginResponse {

    private String token;
    private Long adminId;
    private String username;
    private String nickname;
}
