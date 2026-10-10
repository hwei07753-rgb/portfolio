package com.example.project.entity.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
public class UserLoginRequest {

    @NotBlank(message = "用户名不能为空")
    private String username;

    // R-05-issue-5: 已修复 - 加@Size(min=6,max=100)，与UserRegisterRequest对齐
    @NotBlank(message = "密码不能为空")
    @Size(min = 6, max = 100, message = "密码长度6-100位")
    private String password;
}