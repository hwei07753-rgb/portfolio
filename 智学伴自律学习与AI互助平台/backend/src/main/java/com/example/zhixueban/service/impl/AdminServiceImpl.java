package com.example.zhixueban.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.example.zhixueban.common.BusinessException;
import com.example.zhixueban.common.ErrorCode;
import com.example.zhixueban.entity.Admin;
import com.example.zhixueban.entity.AiReview;
import com.example.zhixueban.entity.AuditLog;
import com.example.zhixueban.entity.Checkin;
import com.example.zhixueban.entity.FocusRecord;
import com.example.zhixueban.entity.Post;
import com.example.zhixueban.entity.SensitiveWord;
import com.example.zhixueban.entity.User;
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
import com.example.zhixueban.enums.UserRoleEnum;
import com.example.zhixueban.enums.UserStatusEnum;
import com.example.zhixueban.mapper.AdminMapper;
import com.example.zhixueban.mapper.AiReviewMapper;
import com.example.zhixueban.mapper.AuditLogMapper;
import com.example.zhixueban.mapper.CheckinMapper;
import com.example.zhixueban.mapper.FocusRecordMapper;
import com.example.zhixueban.mapper.PostMapper;
import com.example.zhixueban.mapper.SensitiveWordMapper;
import com.example.zhixueban.mapper.UserMapper;
import com.example.zhixueban.service.AdminService;
import com.example.zhixueban.util.JwtUtils;
import com.example.zhixueban.util.UserContext;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * 管理员后台服务实现（SRS §3.2 全模块）
 */
@Service
public class AdminServiceImpl implements AdminService {

    private static final Logger log = LoggerFactory.getLogger(AdminServiceImpl.class);

    /** 审核对象类型：1=打卡 2=帖子 */
    private static final int BIZ_TYPE_CHECKIN = 1;
    private static final int BIZ_TYPE_POST = 2;

    private final UserMapper userMapper;
    private final PostMapper postMapper;
    private final CheckinMapper checkinMapper;
    private final FocusRecordMapper focusRecordMapper;
    private final AdminMapper adminMapper;
    private final AuditLogMapper auditLogMapper;
    private final AiReviewMapper aiReviewMapper;
    private final SensitiveWordMapper sensitiveWordMapper;
    private final JwtUtils jwtUtils;
    private final BCryptPasswordEncoder passwordEncoder = new BCryptPasswordEncoder();

    public AdminServiceImpl(UserMapper userMapper,
                            PostMapper postMapper,
                            CheckinMapper checkinMapper,
                            FocusRecordMapper focusRecordMapper,
                            AdminMapper adminMapper,
                            AuditLogMapper auditLogMapper,
                            AiReviewMapper aiReviewMapper,
                            SensitiveWordMapper sensitiveWordMapper,
                            JwtUtils jwtUtils) {
        this.userMapper = userMapper;
        this.postMapper = postMapper;
        this.checkinMapper = checkinMapper;
        this.focusRecordMapper = focusRecordMapper;
        this.adminMapper = adminMapper;
        this.auditLogMapper = auditLogMapper;
        this.aiReviewMapper = aiReviewMapper;
        this.sensitiveWordMapper = sensitiveWordMapper;
        this.jwtUtils = jwtUtils;
    }

    @Override
    public AdminLoginResponse login(AdminLoginRequest request) {
        Admin admin = adminMapper.selectOne(
                new LambdaQueryWrapper<Admin>().eq(Admin::getUsername, request.getUsername().trim()));
        if (admin == null) {
            throw new BusinessException(ErrorCode.ADMIN_LOGIN_FAILED);
        }
        if (admin.getStatus() == null || admin.getStatus() != 1) {
            throw new BusinessException(ErrorCode.ADMIN_DISABLED);
        }
        if (!passwordEncoder.matches(request.getPassword(), admin.getPassword())) {
            throw new BusinessException(ErrorCode.ADMIN_LOGIN_FAILED);
        }

        String token = jwtUtils.generateToken(admin.getId(), UserRoleEnum.ADMIN.getCode());
        log.info("后台管理员登录成功: adminId={}, username={}", admin.getId(), admin.getUsername());
        return AdminLoginResponse.builder()
                .token(token)
                .adminId(admin.getId())
                .username(admin.getUsername())
                .nickname(admin.getNickname())
                .build();
    }

    @Override
    public Page<AdminUserVO> pageUsers(long page, long size, String keyword) {
        requireAdmin();

        LambdaQueryWrapper<User> wrapper = new LambdaQueryWrapper<User>()
                .orderByDesc(User::getCreatedAt);
        if (StringUtils.hasText(keyword)) {
            wrapper.like(User::getNickname, keyword.trim());
        }

        Page<User> userPage = userMapper.selectPage(Page.of(page, size), wrapper);
        Page<AdminUserVO> voPage = new Page<>(userPage.getCurrent(), userPage.getSize(), userPage.getTotal());
        voPage.setRecords(userPage.getRecords().stream().map(AdminUserVO::fromUser).toList());
        return voPage;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void updateUserStatus(Long userId, AdminUserStatusRequest request) {
        requireAdmin();

        User target = userMapper.selectById(userId);
        if (target == null) {
            throw new BusinessException(ErrorCode.USER_NOT_FOUND);
        }
        // 保护规则：不允许封禁管理员账号（防止后台被锁死）
        if (target.getRole() != null && target.getRole() == UserRoleEnum.ADMIN.getCode()) {
            throw new BusinessException(ErrorCode.FORBIDDEN, "不允许操作管理员账号");
        }

        target.setStatus(request.getStatus());
        userMapper.updateById(target);
        log.info("管理员 {} 变更用户 {} 状态为 {}", UserContext.getUserId(), userId,
                request.getStatus() == UserStatusEnum.BANNED.getCode() ? "封禁" : "解封");
    }

    @Override
    public Page<AdminCheckinVO> pageCheckins(long page, long size, Integer status) {
        requireAdmin();

        LambdaQueryWrapper<Checkin> wrapper = new LambdaQueryWrapper<Checkin>()
                .orderByDesc(Checkin::getCreatedAt);
        if (status != null) {
            wrapper.eq(Checkin::getStatus, status);
        }

        Page<Checkin> checkinPage = checkinMapper.selectPage(Page.of(page, size), wrapper);
        List<Checkin> records = checkinPage.getRecords();

        Page<AdminCheckinVO> voPage = new Page<>(checkinPage.getCurrent(), checkinPage.getSize(), checkinPage.getTotal());
        voPage.setRecords(buildCheckinVOs(records));
        return voPage;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void updateCheckinStatus(Long checkinId, AuditRequest request) {
        requireAdmin();

        Checkin checkin = checkinMapper.selectById(checkinId);
        if (checkin == null) {
            throw new BusinessException(ErrorCode.PARAM_ERROR, "打卡记录不存在");
        }
        checkin.setStatus(request.getStatus());
        checkinMapper.updateById(checkin);
        writeAuditLog(BIZ_TYPE_CHECKIN, checkinId, request);
        log.info("管理员 {} 审核打卡 {} -> {}", UserContext.getUserId(), checkinId, request.getStatus());
    }

    @Override
    public Page<AdminPostVO> pagePosts(long page, long size, Integer status) {
        requireAdmin();

        LambdaQueryWrapper<Post> wrapper = new LambdaQueryWrapper<Post>()
                .orderByDesc(Post::getCreatedAt);
        if (status != null) {
            wrapper.eq(Post::getStatus, status);
        }

        Page<Post> postPage = postMapper.selectPage(Page.of(page, size), wrapper);
        List<Post> records = postPage.getRecords();

        Page<AdminPostVO> voPage = new Page<>(postPage.getCurrent(), postPage.getSize(), postPage.getTotal());
        voPage.setRecords(buildPostVOs(records));
        return voPage;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void updatePostStatus(Long postId, AuditRequest request) {
        requireAdmin();

        Post post = postMapper.selectById(postId);
        if (post == null) {
            throw new BusinessException(ErrorCode.POST_NOT_FOUND);
        }
        post.setStatus(request.getStatus());
        postMapper.updateById(post);
        writeAuditLog(BIZ_TYPE_POST, postId, request);
        log.info("管理员 {} 审核帖子 {} -> {}", UserContext.getUserId(), postId, request.getStatus());
    }

    @Override
    public Page<AdminAuditLogVO> pageAuditLogs(long page, long size) {
        requireAdmin();

        Page<AuditLog> auditPage = auditLogMapper.selectPage(
                Page.of(page, size),
                new LambdaQueryWrapper<AuditLog>().orderByDesc(AuditLog::getCreatedAt));
        List<AuditLog> records = auditPage.getRecords();

        Map<Long, String> adminNameMap = records.isEmpty() ? Map.of()
                : adminMapper.selectBatchIds(records.stream().map(AuditLog::getAdminId).distinct().toList())
                        .stream()
                        .collect(Collectors.toMap(Admin::getId, a -> a.getNickname() != null ? a.getNickname() : a.getUsername()));

        Page<AdminAuditLogVO> voPage = new Page<>(auditPage.getCurrent(), auditPage.getSize(), auditPage.getTotal());
        voPage.setRecords(records.stream().map(a -> AdminAuditLogVO.builder()
                .id(a.getId())
                .bizType(a.getBizType())
                .bizId(a.getBizId())
                .adminId(a.getAdminId())
                .adminName(adminNameMap.getOrDefault(a.getAdminId(), "管理员"))
                .action(a.getAction())
                .reason(a.getReason())
                .createdAt(a.getCreatedAt())
                .build()).toList());
        return voPage;
    }

    @Override
    public Page<SensitiveWord> pageSensitiveWords(long page, long size, String keyword) {
        requireAdmin();

        LambdaQueryWrapper<SensitiveWord> wrapper = new LambdaQueryWrapper<SensitiveWord>()
                .orderByDesc(SensitiveWord::getId);
        if (StringUtils.hasText(keyword)) {
            wrapper.like(SensitiveWord::getWord, keyword.trim());
        }
        return sensitiveWordMapper.selectPage(Page.of(page, size), wrapper);
    }

    @Override
    public void addSensitiveWord(SensitiveWordRequest request) {
        requireAdmin();

        try {
            sensitiveWordMapper.insert(SensitiveWord.builder()
                    .word(request.getWord().trim())
                    .status(1)
                    .createdAt(LocalDateTime.now())
                    .build());
        } catch (DuplicateKeyException e) {
            throw new BusinessException(ErrorCode.PARAM_ERROR, "敏感词已存在");
        }
    }

    @Override
    public void updateSensitiveWordStatus(Long id, Integer status) {
        requireAdmin();

        SensitiveWord word = sensitiveWordMapper.selectById(id);
        if (word == null) {
            throw new BusinessException(ErrorCode.PARAM_ERROR, "敏感词不存在");
        }
        word.setStatus(status);
        sensitiveWordMapper.updateById(word);
    }

    @Override
    public AdminStatsResponse getAdminStats() {
        requireAdmin();

        Long userCount = userMapper.selectCount(null);
        Long postCount = postMapper.selectCount(
                new LambdaQueryWrapper<Post>().ne(Post::getStatus, 2)
        );
        Long checkinCount = checkinMapper.selectCount(null);
        Long aiReviewCount = aiReviewMapper.selectCount(null);

        // 今日打卡数（SRS §3.2.4）
        LocalDateTime dayStart = LocalDateTime.of(LocalDate.now(), LocalTime.MIN);
        LocalDateTime dayEnd = dayStart.plusDays(1);
        Long todayCheckinCount = checkinMapper.selectCount(
                new LambdaQueryWrapper<Checkin>()
                        .ge(Checkin::getCreatedAt, dayStart)
                        .lt(Checkin::getCreatedAt, dayEnd)
        );

        // 平台专注总时长：仅统计"完成"（status=0）的记录
        List<FocusRecord> focusRecords = focusRecordMapper.selectList(
                new LambdaQueryWrapper<FocusRecord>().eq(FocusRecord::getStatus, 0)
        );
        int focusTotalMinutes = focusRecords.stream()
                .mapToInt(r -> r.getDurationMinutes() != null ? r.getDurationMinutes() : 0)
                .sum();

        return AdminStatsResponse.builder()
                .userCount(userCount != null ? userCount : 0L)
                .postCount(postCount != null ? postCount : 0L)
                .checkinCount(checkinCount != null ? checkinCount : 0L)
                .todayCheckinCount(todayCheckinCount != null ? todayCheckinCount : 0L)
                .aiReviewCount(aiReviewCount != null ? aiReviewCount : 0L)
                .focusTotalMinutes(focusTotalMinutes)
                .build();
    }

    /**
     * 打卡审核列表 VO 构建：回填用户昵称 + AI 复盘（批量查，避免 N+1）
     */
    private List<AdminCheckinVO> buildCheckinVOs(List<Checkin> records) {
        if (records.isEmpty()) {
            return List.of();
        }
        Map<Long, String> nicknameMap = nicknameMap(records.stream().map(Checkin::getUserId).distinct().toList());
        Map<Long, String> reviewMap = aiReviewMapper.selectList(
                        new LambdaQueryWrapper<AiReview>()
                                .in(AiReview::getCheckinId, records.stream().map(Checkin::getId).toList()))
                .stream()
                .collect(Collectors.toMap(AiReview::getCheckinId, AiReview::getContent, (a, b) -> a));

        return records.stream().map(c -> AdminCheckinVO.builder()
                .id(c.getId())
                .userId(c.getUserId())
                .userNickname(nicknameMap.getOrDefault(c.getUserId(), "学伴"))
                .content(c.getContent())
                .imageUrl(c.getImageUrl())
                .aiReview(reviewMap.get(c.getId()))
                .status(c.getStatus())
                .createdAt(c.getCreatedAt())
                .build()).toList();
    }

    /**
     * 帖子审核列表 VO 构建：回填用户昵称（批量查）
     */
    private List<AdminPostVO> buildPostVOs(List<Post> records) {
        if (records.isEmpty()) {
            return List.of();
        }
        Map<Long, String> nicknameMap = nicknameMap(records.stream().map(Post::getUserId).distinct().toList());
        return records.stream().map(p -> AdminPostVO.builder()
                .id(p.getId())
                .userId(p.getUserId())
                .userNickname(nicknameMap.getOrDefault(p.getUserId(), "学伴"))
                .category(p.getCategory())
                .title(p.getTitle())
                .content(p.getContent())
                .status(p.getStatus())
                .createdAt(p.getCreatedAt())
                .build()).toList();
    }

    private Map<Long, String> nicknameMap(List<Long> userIds) {
        if (userIds.isEmpty()) {
            return Map.of();
        }
        return userMapper.selectBatchIds(userIds).stream()
                .collect(Collectors.toMap(User::getId,
                        u -> u.getNickname() != null ? u.getNickname() : "学伴"));
    }

    /**
     * 写审核留痕（audit_log）
     */
    private void writeAuditLog(Integer bizType, Long bizId, AuditRequest request) {
        auditLogMapper.insert(AuditLog.builder()
                .bizType(bizType)
                .bizId(bizId)
                .adminId(UserContext.getUserId())
                .action(request.getStatus())
                .reason(StringUtils.hasText(request.getReason()) ? request.getReason().trim() : null)
                .createdAt(LocalDateTime.now())
                .build());
    }

    /**
     * 管理员身份校验：当前登录用户必须是管理员（role=1）
     */
    private void requireAdmin() {
        Integer role = UserContext.getRole();
        if (role == null || role != UserRoleEnum.ADMIN.getCode()) {
            throw new BusinessException(ErrorCode.FORBIDDEN);
        }
    }
}
