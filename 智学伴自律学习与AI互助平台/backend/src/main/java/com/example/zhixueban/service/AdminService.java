package com.example.zhixueban.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
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

/**
 * 管理员后台服务
 */
public interface AdminService {

    /**
     * 后台管理员账号密码登录（SRS §3.2.1），签发管理员 JWT
     */
    AdminLoginResponse login(AdminLoginRequest request);

    /**
     * 分页获取用户列表（openid 脱敏）
     *
     * @param page    页码（从 1 开始）
     * @param size    每页条数
     * @param keyword 昵称模糊关键字（可空）
     * @return 分页结果
     */
    Page<AdminUserVO> pageUsers(long page, long size, String keyword);

    /**
     * 变更用户状态：封禁（status=1）/ 解封（status=0）
     *
     * @param userId  目标用户 ID
     * @param request 目标状态
     */
    void updateUserStatus(Long userId, AdminUserStatusRequest request);

    /**
     * 分页获取打卡审核列表（SRS §3.2.3，可按状态筛选）
     */
    Page<AdminCheckinVO> pageCheckins(long page, long size, Integer status);

    /**
     * 打卡审核：通过（status=1）/ 删除（status=2），写审核留痕
     */
    void updateCheckinStatus(Long checkinId, AuditRequest request);

    /**
     * 分页获取帖子审核列表（SRS §3.2.3，可按状态筛选）
     */
    Page<AdminPostVO> pagePosts(long page, long size, Integer status);

    /**
     * 帖子审核：通过（status=1）/ 删除（status=2），写审核留痕
     */
    void updatePostStatus(Long postId, AuditRequest request);

    /**
     * 分页查询审核记录（audit_log 留痕）
     */
    Page<AdminAuditLogVO> pageAuditLogs(long page, long size);

    /**
     * 分页获取敏感词列表（SRS §6.2.2 后台维护）
     */
    Page<SensitiveWord> pageSensitiveWords(long page, long size, String keyword);

    /**
     * 新增敏感词（名称唯一）
     */
    void addSensitiveWord(SensitiveWordRequest request);

    /**
     * 敏感词启用/停用（status=1/0）
     */
    void updateSensitiveWordStatus(Long id, Integer status);

    /**
     * 获取平台核心宏观指标（SRS §3.2.4：用户数/今日打卡/帖子/AI调用/专注时长）
     */
    AdminStatsResponse getAdminStats();
}
