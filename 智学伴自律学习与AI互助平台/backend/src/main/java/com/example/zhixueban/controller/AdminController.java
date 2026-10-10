package com.example.zhixueban.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.example.zhixueban.common.Result;
import com.example.zhixueban.entity.SensitiveWord;
import com.example.zhixueban.entity.dto.AdminAuditLogVO;
import com.example.zhixueban.entity.dto.AdminCheckinVO;
import com.example.zhixueban.entity.dto.AdminLoginRequest;
import com.example.zhixueban.entity.dto.AdminLoginResponse;
import com.example.zhixueban.entity.dto.AdminPostVO;
import com.example.zhixueban.entity.dto.AdminStatsResponse;
import com.example.zhixueban.entity.dto.AdminUserStatusRequest;
import com.example.zhixueban.entity.dto.AdminUserVO;
import com.example.zhixueban.entity.dto.AuditRequest;
import com.example.zhixueban.entity.dto.SensitiveWordRequest;
import com.example.zhixueban.service.AdminService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 管理员后台接口（除 login 外全部需登录且 role=1，非管理员返回 1002 无权操作）
 * <p>
 * 对应 SRS §3.2：管理员登录 / 用户管理 / 内容审核 / 简单统计
 */
@RestController
@RequestMapping("/api/admin")
public class AdminController {

    private final AdminService adminService;

    public AdminController(AdminService adminService) {
        this.adminService = adminService;
    }

    /** 后台管理员账号密码登录（SRS §3.2.1，白名单放行） */
    @PostMapping("/login")
    public Result<AdminLoginResponse> login(@Valid @RequestBody AdminLoginRequest request) {
        return Result.success(adminService.login(request), "登录成功");
    }

    /**
     * 分页获取系统用户列表
     */
    @GetMapping("/users")
    public Result<Page<AdminUserVO>> pageUsers(
            @RequestParam(defaultValue = "1") @Min(value = 1, message = "页码从 1 开始") long page,
            @RequestParam(defaultValue = "10") @Min(value = 1, message = "每页至少 1 条")
            @Max(value = 50, message = "每页最多 50 条") long size,
            @RequestParam(required = false) String keyword) {
        return Result.success(adminService.pageUsers(page, size, keyword));
    }

    /**
     * 变更用户状态：封禁（status=1）/ 解封（status=0）
     */
    @PutMapping("/user/{id}/status")
    public Result<Void> updateUserStatus(@PathVariable Long id,
                                         @RequestBody @Valid AdminUserStatusRequest request) {
        adminService.updateUserStatus(id, request);
        return Result.success(null, "用户状态更新成功");
    }

    /**
     * 分页获取打卡审核列表（SRS §3.2.3，可按状态筛选）
     */
    @GetMapping("/checkins")
    public Result<Page<AdminCheckinVO>> pageCheckins(
            @RequestParam(defaultValue = "1") @Min(value = 1, message = "页码从 1 开始") long page,
            @RequestParam(defaultValue = "10") @Min(value = 1, message = "每页至少 1 条")
            @Max(value = 50, message = "每页最多 50 条") long size,
            @RequestParam(required = false) Integer status) {
        return Result.success(adminService.pageCheckins(page, size, status));
    }

    /**
     * 打卡审核：通过（status=1）/ 删除（status=2）
     */
    @PutMapping("/checkin/{id}/status")
    public Result<Void> updateCheckinStatus(@PathVariable Long id,
                                            @RequestBody @Valid AuditRequest request) {
        adminService.updateCheckinStatus(id, request);
        return Result.success(null, "打卡审核完成");
    }

    /**
     * 分页获取帖子审核列表（SRS §3.2.3，可按状态筛选）
     */
    @GetMapping("/posts")
    public Result<Page<AdminPostVO>> pagePosts(
            @RequestParam(defaultValue = "1") @Min(value = 1, message = "页码从 1 开始") long page,
            @RequestParam(defaultValue = "10") @Min(value = 1, message = "每页至少 1 条")
            @Max(value = 50, message = "每页最多 50 条") long size,
            @RequestParam(required = false) Integer status) {
        return Result.success(adminService.pagePosts(page, size, status));
    }

    /**
     * 帖子审核：通过（status=1）/ 删除（status=2）
     */
    @PutMapping("/post/{id}/status")
    public Result<Void> updatePostStatus(@PathVariable Long id,
                                         @RequestBody @Valid AuditRequest request) {
        adminService.updatePostStatus(id, request);
        return Result.success(null, "帖子审核完成");
    }

    /**
     * 分页查询审核记录（留痕）
     */
    @GetMapping("/audit-logs")
    public Result<Page<AdminAuditLogVO>> pageAuditLogs(
            @RequestParam(defaultValue = "1") @Min(value = 1, message = "页码从 1 开始") long page,
            @RequestParam(defaultValue = "10") @Min(value = 1, message = "每页至少 1 条")
            @Max(value = 50, message = "每页最多 50 条") long size) {
        return Result.success(adminService.pageAuditLogs(page, size));
    }

    /**
     * 分页获取敏感词列表（SRS §6.2.2 后台维护）
     */
    @GetMapping("/sensitive-words")
    public Result<Page<SensitiveWord>> pageSensitiveWords(
            @RequestParam(defaultValue = "1") @Min(value = 1, message = "页码从 1 开始") long page,
            @RequestParam(defaultValue = "10") @Min(value = 1, message = "每页至少 1 条")
            @Max(value = 50, message = "每页最多 50 条") long size,
            @RequestParam(required = false) String keyword) {
        return Result.success(adminService.pageSensitiveWords(page, size, keyword));
    }

    /**
     * 新增敏感词
     */
    @PostMapping("/sensitive-words")
    public Result<Void> addSensitiveWord(@Valid @RequestBody SensitiveWordRequest request) {
        adminService.addSensitiveWord(request);
        return Result.success(null, "敏感词添加成功");
    }

    /**
     * 敏感词启用/停用（status=1/0）
     */
    @PutMapping("/sensitive-word/{id}/status")
    public Result<Void> updateSensitiveWordStatus(@PathVariable Long id,
                                                  @RequestParam @Min(value = 0, message = "状态取值 0/1")
                                                  @Max(value = 1, message = "状态取值 0/1") Integer status) {
        adminService.updateSensitiveWordStatus(id, status);
        return Result.success(null, "敏感词状态更新成功");
    }

    /**
     * 平台核心宏观指标（SRS §3.2.4）
     */
    @GetMapping("/stats")
    public Result<AdminStatsResponse> getAdminStats() {
        return Result.success(adminService.getAdminStats());
    }
}
