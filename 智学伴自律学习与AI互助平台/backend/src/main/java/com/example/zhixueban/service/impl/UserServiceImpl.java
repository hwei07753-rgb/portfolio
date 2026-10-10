package com.example.zhixueban.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.example.zhixueban.common.BusinessException;
import com.example.zhixueban.common.ErrorCode;
import com.example.zhixueban.entity.Checkin;
import com.example.zhixueban.entity.FocusRecord;
import com.example.zhixueban.entity.Post;
import com.example.zhixueban.entity.User;
import com.example.zhixueban.entity.dto.LoginResponse;
import com.example.zhixueban.entity.dto.UserProfileUpdateRequest;
import com.example.zhixueban.entity.dto.UserStatsResponse;
import com.example.zhixueban.entity.dto.UserVO;
import com.example.zhixueban.entity.dto.WxLoginRequest;
import com.example.zhixueban.mapper.CheckinMapper;
import com.example.zhixueban.mapper.FocusRecordMapper;
import com.example.zhixueban.mapper.PostMapper;
import com.example.zhixueban.mapper.UserMapper;
import com.example.zhixueban.service.UserService;
import com.example.zhixueban.util.JwtUtils;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.time.LocalDateTime;
import java.util.List;

@Service
public class UserServiceImpl implements UserService {

    private static final Logger log = LoggerFactory.getLogger(UserServiceImpl.class);

    private final UserMapper userMapper;
    private final FocusRecordMapper focusRecordMapper;
    private final CheckinMapper checkinMapper;
    private final PostMapper postMapper;
    private final JwtUtils jwtUtils;
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Value("${wx.miniapp.appid:}")
    private String appId;

    @Value("${wx.miniapp.secret:}")
    private String appSecret;

    public UserServiceImpl(UserMapper userMapper,
                           FocusRecordMapper focusRecordMapper,
                           CheckinMapper checkinMapper,
                           PostMapper postMapper,
                           JwtUtils jwtUtils) {
        this.userMapper = userMapper;
        this.focusRecordMapper = focusRecordMapper;
        this.checkinMapper = checkinMapper;
        this.postMapper = postMapper;
        this.jwtUtils = jwtUtils;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public LoginResponse wxLogin(WxLoginRequest request) {
        String code = request.getCode().trim();
        String openid = resolveWxOpenid(code);

        if (!StringUtils.hasText(openid)) {
            throw new BusinessException(ErrorCode.WX_LOGIN_FAILED, "获取微信用户标识失败");
        }

        // 查询数据库中是否已有该用户
        User user = userMapper.selectOne(
                new LambdaQueryWrapper<User>().eq(User::getOpenid, openid)
        );

        if (user == null) {
            // 新用户自动注册落库
            user = User.builder()
                    .openid(openid)
                    .nickname("自律学伴_" + Math.abs(openid.hashCode() % 10000))
                    .avatarUrl("/images/tabbar/mine.png")
                    .studyGoal("2027考研 / 四六级通关")
                    .role(0) // 学员角色
                    .status(0) // 正常状态
                    .coins(100) // 初始自律积分
                    .createdAt(LocalDateTime.now())
                    .build();
            userMapper.insert(user);
            log.info("新微信用户注册成功: id={}, openid={}", user.getId(), openid);
        } else {
            // 校验账号状态
            if (user.getStatus() != null && user.getStatus() == 1) {
                throw new BusinessException(ErrorCode.USER_BANNED);
            }
        }

        // 签发 JWT
        String token = jwtUtils.generateToken(user.getId(), user.getRole());
        return LoginResponse.builder()
                .token(token)
                .user(UserVO.fromUser(user))
                .build();
    }

    @Override
    public UserVO getUserInfo(Long userId) {
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw new BusinessException(ErrorCode.USER_NOT_FOUND);
        }
        return UserVO.fromUser(user);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void updateProfile(Long userId, UserProfileUpdateRequest request) {
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw new BusinessException(ErrorCode.USER_NOT_FOUND);
        }

        boolean updated = false;
        if (StringUtils.hasText(request.getNickname())) {
            user.setNickname(request.getNickname().trim());
            updated = true;
        }
        if (StringUtils.hasText(request.getAvatarUrl())) {
            user.setAvatarUrl(request.getAvatarUrl().trim());
            updated = true;
        }
        if (StringUtils.hasText(request.getStudyGoal())) {
            user.setStudyGoal(request.getStudyGoal().trim());
            updated = true;
        }

        if (updated) {
            userMapper.updateById(user);
            log.info("用户资料更新成功: userId={}", userId);
        }
    }

    @Override
    public UserStatsResponse getUserStats(Long userId) {
        // 1. 累计专注时长（状态为0=完成的记录）
        List<FocusRecord> focusRecords = focusRecordMapper.selectList(
                new LambdaQueryWrapper<FocusRecord>()
                        .eq(FocusRecord::getUserId, userId)
                        .eq(FocusRecord::getStatus, 0)
        );
        int totalMinutes = focusRecords.stream()
                .mapToInt(r -> r.getDurationMinutes() != null ? r.getDurationMinutes() : 0)
                .sum();

        // 2. 累计打卡次数
        Long checkinCount = checkinMapper.selectCount(
                new LambdaQueryWrapper<Checkin>()
                        .eq(Checkin::getUserId, userId)
        );

        // 3. 累计社区发帖数（未被删除的记录）
        Long postCount = postMapper.selectCount(
                new LambdaQueryWrapper<Post>()
                        .eq(Post::getUserId, userId)
                        .ne(Post::getStatus, 2)
        );

        // 4. 用户当前自律积分
        User user = userMapper.selectById(userId);
        int coins = (user != null && user.getCoins() != null) ? user.getCoins() : 0;

        return UserStatsResponse.builder()
                .totalMinutes(totalMinutes)
                .totalCheckins(checkinCount != null ? checkinCount.intValue() : 0)
                .totalPosts(postCount != null ? postCount.intValue() : 0)
                .coins(coins)
                .build();
    }

    /**
     * 将微信授权 code 换取真实或联调 openid
     */
    private String resolveWxOpenid(String code) {
        // 1. 优先支持测试种子与演示模式特定 openid
        if (code.startsWith("demo_openid_") || code.startsWith("admin_openid_")) {
            return code;
        }
        if (code.startsWith("mock_")) {
            return "wx_mock_user_" + code.substring(5);
        }

        // 2. 若配置了非 demo 的微信 AppId 与 Secret，则发起官方 API 交互
        if (StringUtils.hasText(appId) && StringUtils.hasText(appSecret)
                && !appId.contains("demo") && !appSecret.contains("demo")) {
            try {
                String url = String.format(
                        "https://api.weixin.qq.com/sns/jscode2session?appid=%s&secret=%s&js_code=%s&grant_type=authorization_code",
                        appId, appSecret, code
                );
                HttpClient client = HttpClient.newBuilder()
                        .connectTimeout(Duration.ofSeconds(5))
                        .build();
                HttpRequest req = HttpRequest.newBuilder()
                        .uri(URI.create(url))
                        .GET()
                        .timeout(Duration.ofSeconds(5))
                        .build();
                HttpResponse<String> resp = client.send(req, HttpResponse.BodyHandlers.ofString());
                if (resp.statusCode() == 200) {
                    JsonNode node = objectMapper.readTree(resp.body());
                    if (node.has("openid")) {
                        return node.get("openid").asText();
                    }
                    log.warn("微信官方换取 openid 响应返回错误: {}", resp.body());
                }
            } catch (Exception e) {
                log.warn("调用微信官方接口异常，降级至开发联调 openid 模式: {}", e.getMessage());
            }
        }

        // 3. 开发联调/课设演示兜底模式：基于 code 确定性生成专属 openid
        return "wx_openid_dev_" + Math.abs(code.hashCode());
    }
}
