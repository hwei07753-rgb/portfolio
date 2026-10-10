package com.example.zhixueban.controller;

import com.example.zhixueban.common.Result;
import com.example.zhixueban.entity.dto.LoginResponse;
import com.example.zhixueban.entity.dto.WxLoginRequest;
import com.example.zhixueban.service.UserService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final UserService userService;

    public AuthController(UserService userService) {
        this.userService = userService;
    }

    /**
     * 微信快捷登录（对齐总体设计契约 /api/auth/login）
     */
    @PostMapping("/login")
    public Result<LoginResponse> login(@Valid @RequestBody WxLoginRequest request) {
        LoginResponse response = userService.wxLogin(request);
        return Result.success(response, "登录成功");
    }
}
