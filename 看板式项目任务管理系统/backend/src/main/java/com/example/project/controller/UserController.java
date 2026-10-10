package com.example.project.controller;

import com.example.project.common.BusinessException;
import com.example.project.common.Result;
import com.example.project.entity.User;
import com.example.project.entity.dto.ChangePasswordRequest;
import com.example.project.entity.dto.UpdateProfileRequest;
import com.example.project.entity.dto.UserVO;
import com.example.project.service.UserService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestAttribute;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/users")
@RequiredArgsConstructor
public class UserController {

    private final UserService userService;

    // R-05-issue-2: 已修复 - 返回Result<UserVO>代替Result<User>，不暴露isDeleted内部字段，对齐API_DESIGN §3.1响应字段规范
    // R-05-issue-3: 已修复 - getById返回null时抛BusinessException(1004)，前端不会收到code=200但data=null的歧义响应
    @GetMapping("/me")
    public Result<UserVO> me(@RequestAttribute("userId") Long userId) {
        User user = userService.getById(userId);
        if (user == null) {
            throw new BusinessException(1004, "用户不存在");
        }
        UserVO vo = new UserVO();
        vo.setId(user.getId());
        vo.setUsername(user.getUsername());
        vo.setNickname(user.getNickname());
        vo.setEmail(user.getEmail());
        vo.setCreateTime(user.getCreateTime());
        return Result.success(vo);
    }

    /** 按用户名精确搜索用户（用于成员管理中添加成员） */
    @GetMapping("/search")
    public Result<List<UserVO>> search(
            @RequestAttribute("userId") Long userId,
            @RequestParam String keyword) {
        List<User> users = userService.searchByUsername(keyword);
        List<UserVO> vos = users.stream().map(u -> {
            UserVO vo = new UserVO();
            vo.setId(u.getId());
            vo.setUsername(u.getUsername());
            vo.setNickname(u.getNickname());
            return vo;
        }).toList();
        return Result.success(vos);
    }

    /** 修改个人资料（昵称 + 邮箱） */
    @PutMapping("/me")
    public Result<Void> updateProfile(
            @RequestAttribute("userId") Long userId,
            @RequestBody @Valid UpdateProfileRequest request) {
        userService.updateProfile(userId, request.getNickname(), request.getEmail());
        return Result.success(null, "修改成功");
    }

    /** 修改密码 */
    @PutMapping("/me/password")
    public Result<Void> changePassword(
            @RequestAttribute("userId") Long userId,
            @RequestBody @Valid ChangePasswordRequest request) {
        userService.changePassword(userId, request.getOldPassword(), request.getNewPassword());
        return Result.success(null, "密码修改成功");
    }
}