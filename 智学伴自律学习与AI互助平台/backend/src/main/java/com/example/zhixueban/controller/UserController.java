package com.example.zhixueban.controller;

import com.example.zhixueban.common.Result;
import com.example.zhixueban.entity.dto.LoginResponse;
import com.example.zhixueban.entity.dto.UserProfileUpdateRequest;
import com.example.zhixueban.entity.dto.UserStatsResponse;
import com.example.zhixueban.entity.dto.UserVO;
import com.example.zhixueban.entity.dto.WxLoginRequest;
import com.example.zhixueban.service.UserService;
import com.example.zhixueban.util.UserContext;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/user")
public class UserController {

    private final UserService userService;

    public UserController(UserService userService) {
        this.userService = userService;
    }

    /**
     * 微信授权登录（小程序端直接调用）
     */
    @PostMapping("/wx-login")
    public Result<LoginResponse> wxLogin(@Valid @RequestBody WxLoginRequest request) {
        LoginResponse response = userService.wxLogin(request);
        return Result.success(response, "登录成功");
    }

    /**
     * 获取当前登录用户信息
     */
    @GetMapping("/info")
    public Result<UserVO> getUserInfo() {
        Long currentUserId = UserContext.getUserId();
        UserVO userVO = userService.getUserInfo(currentUserId);
        return Result.success(userVO);
    }

    /**
     * 修改个人资料与学习目标
     */
    @PutMapping("/profile")
    public Result<Void> updateProfile(@RequestBody UserProfileUpdateRequest request) {
        Long currentUserId = UserContext.getUserId();
        userService.updateProfile(currentUserId, request);
        return Result.success(null, "个人资料更新成功");
    }

    /**
     * 获取用户个人学习统计数据（累计专注时长、打卡数、发帖数）
     */
    @GetMapping("/stats")
    public Result<UserStatsResponse> getUserStats() {
        Long currentUserId = UserContext.getUserId();
        UserStatsResponse stats = userService.getUserStats(currentUserId);
        return Result.success(stats);
    }
}
