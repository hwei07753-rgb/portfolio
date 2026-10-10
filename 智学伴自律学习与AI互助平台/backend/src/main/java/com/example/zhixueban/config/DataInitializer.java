package com.example.zhixueban.config;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.example.zhixueban.entity.Admin;
import com.example.zhixueban.mapper.AdminMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.CommandLineRunner;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;

/**
 * 启动初始化：admin 表为空时创建默认管理员（admin / 123456，密码 BCrypt 加密）
 * <p>
 * 说明：默认密码仅用于课设演示，密码不落盘为明文（符合宪法 §5.6）；
 * 首次启动写入一次，之后不再覆盖。
 */
@Component
public class DataInitializer implements CommandLineRunner {

    private static final Logger log = LoggerFactory.getLogger(DataInitializer.class);

    private final AdminMapper adminMapper;
    private final com.example.zhixueban.mapper.UserMapper userMapper;
    private final BCryptPasswordEncoder passwordEncoder = new BCryptPasswordEncoder();

    public DataInitializer(AdminMapper adminMapper, com.example.zhixueban.mapper.UserMapper userMapper) {
        this.adminMapper = adminMapper;
        this.userMapper = userMapper;
    }

    @Override
    public void run(String... args) {
        // 1. 初始化管理员账号
        Long count = adminMapper.selectCount(new LambdaQueryWrapper<Admin>());
        if (count == null || count == 0) {
            Admin admin = Admin.builder()
                    .username("admin")
                    .password(passwordEncoder.encode("123456"))
                    .nickname("系统管理员")
                    .status(1)
                    .createdAt(LocalDateTime.now())
                    .updatedAt(LocalDateTime.now())
                    .build();
            adminMapper.insert(admin);
            log.info("已初始化默认管理员账号：admin（密码 BCrypt 加密存储）");
        }

        // 2. 初始化 AI 助教官方虚拟用户
        com.example.zhixueban.entity.User aiBot = userMapper.selectOne(
                new LambdaQueryWrapper<com.example.zhixueban.entity.User>().eq(com.example.zhixueban.entity.User::getOpenid, "ai_assistant_bot"));
        if (aiBot == null) {
            aiBot = com.example.zhixueban.entity.User.builder()
                    .openid("ai_assistant_bot")
                    .nickname("智学伴 AI 助教")
                    .avatarUrl("/images/tabbar/ai-avatar.png")
                    .studyGoal("随时为同学们解答学业疑惑与考研难点")
                    .role(0)
                    .status(0)
                    .createdAt(LocalDateTime.now())
                    .build();
            userMapper.insert(aiBot);
            log.info("已初始化系统内置角色：智学伴 AI 助教（userId={}）", aiBot.getId());
        }
    }
}
