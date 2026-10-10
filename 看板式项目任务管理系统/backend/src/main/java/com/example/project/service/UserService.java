package com.example.project.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.example.project.entity.User;
import com.example.project.entity.dto.UserLoginRequest;
import com.example.project.entity.dto.UserLoginResponse;
import com.example.project.entity.dto.UserRegisterRequest;

import java.util.List;

public interface UserService extends IService<User> {

    /** 注册，返回注册成功的用户（不含密码） */
    User register(UserRegisterRequest request);

    /** 登录，返回 JWT token + 用户信息 */
    UserLoginResponse login(UserLoginRequest request);

    /** 根据用户名查用户（含密码，用于登录校验） */
    User getByUsernameWithPassword(String username);

    /** 根据用户名关键词搜索用户（精确匹配，用于成员添加） */
    List<User> searchByUsername(String keyword);

    /** 修改个人资料（昵称 + 邮箱） */
    void updateProfile(Long userId, String nickname, String email);

    /** 修改密码（验证原密码后更新） */
    void changePassword(Long userId, String oldPassword, String newPassword);
}