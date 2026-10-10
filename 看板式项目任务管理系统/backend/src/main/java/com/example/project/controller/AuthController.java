package com.example.project.controller;

import com.example.project.common.Result;
import com.example.project.entity.User;
import com.example.project.entity.dto.UserLoginRequest;
import com.example.project.entity.dto.UserLoginResponse;
import com.example.project.entity.dto.UserRegisterRequest;
import com.example.project.service.UserService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final UserService userService;

    /** 注册 */
    @PostMapping("/register")
    public Result<Void> register(@RequestBody @Valid UserRegisterRequest request) {
        userService.register(request);
        return Result.success(null, "注册成功");
    }

    /** 登录 */
    @PostMapping("/login")
    public Result<UserLoginResponse> login(@RequestBody @Valid UserLoginRequest request) {
        UserLoginResponse response = userService.login(request);
        return Result.success(response, "登录成功");
    }
}