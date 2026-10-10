package com.example.zhixueban.service;

import com.example.zhixueban.entity.dto.LoginResponse;
import com.example.zhixueban.entity.dto.UserProfileUpdateRequest;
import com.example.zhixueban.entity.dto.UserStatsResponse;
import com.example.zhixueban.entity.dto.UserVO;
import com.example.zhixueban.entity.dto.WxLoginRequest;

public interface UserService {

    /**
     * 微信授权登录 / 开发联调登录
     *
     * @param request 包含微信 code
     * @return 登录令牌与用户信息
     */
    LoginResponse wxLogin(WxLoginRequest request);

    /**
     * 获取当前用户信息
     *
     * @param userId 用户 ID
     * @return 用户详情 VO
     */
    UserVO getUserInfo(Long userId);

    /**
     * 修改个人资料
     *
     * @param userId  用户 ID
     * @param request 修改参数
     */
    void updateProfile(Long userId, UserProfileUpdateRequest request);

    /**
     * 获取个人累计学习统计数据
     *
     * @param userId 用户 ID
     * @return 统计数据 VO
     */
    UserStatsResponse getUserStats(Long userId);
}
