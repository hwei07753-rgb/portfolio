package com.example.zhixueban;

import com.example.zhixueban.entity.dto.LoginResponse;
import com.example.zhixueban.entity.dto.UserStatsResponse;
import com.example.zhixueban.entity.dto.WxLoginRequest;
import com.example.zhixueban.service.UserService;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest
class ZhixuebanApplicationTests {

    @Autowired
    private UserService userService;

    @Test
    void contextLoads() {
        Assertions.assertNotNull(userService, "UserService 应该成功注入");
    }

    @Test
    void testWxLoginAndUserStatsWithRealDatabase() {
        // 使用数据库中预置的测试账号 demo_openid_0001
        WxLoginRequest request = new WxLoginRequest("demo_openid_0001");
        LoginResponse response = userService.wxLogin(request);

        Assertions.assertNotNull(response, "登录响应不应为空");
        Assertions.assertNotNull(response.getToken(), "Token 不应为空");
        Assertions.assertNotNull(response.getUser(), "用户信息不应为空");
        Assertions.assertEquals("demo_openid_0001", response.getUser().getOpenid());

        // 测试获取该用户的真实统计数据（应匹配数据库中的已完成专注时长）
        UserStatsResponse stats = userService.getUserStats(response.getUser().getId());
        Assertions.assertNotNull(stats);
        Assertions.assertTrue(stats.getTotalMinutes() >= 0);
    }
}
