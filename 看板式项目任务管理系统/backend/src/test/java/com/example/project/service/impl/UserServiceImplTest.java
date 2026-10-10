package com.example.project.service.impl;

import com.example.project.common.BusinessException;
import com.example.project.entity.User;
import com.example.project.entity.dto.UserLoginRequest;
import com.example.project.entity.dto.UserRegisterRequest;
import com.example.project.mapper.UserMapper;
import com.example.project.util.JwtUtils;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.test.util.ReflectionTestUtils;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.when;

// R-05-issue-3: 已修复 - 补充password=NULL空值防御测试 shouldRejectNullPasswordInDB
@ExtendWith(MockitoExtension.class)
@DisplayName("用户服务单元测试")
class UserServiceImplTest {

    @Mock
    private UserMapper userMapper;

    @Mock
    private JwtUtils jwtUtils;

    private UserServiceImpl userService;

    @BeforeEach
    void setUp() {
        userService = new UserServiceImpl(jwtUtils);
        ReflectionTestUtils.setField(userService, "baseMapper", userMapper);
        lenient().when(jwtUtils.generateToken(anyLong())).thenReturn("mock-jwt-token");
    }

    @Test
    @DisplayName("注册 - 正常流程")
    void shouldRegisterSuccessfully() {
        UserRegisterRequest req = new UserRegisterRequest();
        req.setUsername("newuser");
        req.setPassword("123456");

        when(userMapper.selectCount(any())).thenReturn(0L);
        when(userMapper.insert(any(User.class))).thenReturn(1);

        User result = userService.register(req);

        assertThat(result.getUsername()).isEqualTo("newuser");
        assertThat(result.getPassword()).isNull();
    }

    @Test
    @DisplayName("注册 - 用户名已存在（查重抛出）")
    void shouldRejectDuplicateUsernameOnCheck() {
        UserRegisterRequest req = new UserRegisterRequest();
        req.setUsername("admin");
        req.setPassword("123456");

        when(userMapper.selectCount(any())).thenReturn(1L);

        assertThatThrownBy(() -> userService.register(req))
                .isInstanceOf(BusinessException.class)
                .extracting("code").isEqualTo(1001);
    }

    @Test
    @DisplayName("注册 - 并发重复插入（DuplicateKeyException）")
    void shouldRejectDuplicateUsernameOnInsert() {
        UserRegisterRequest req = new UserRegisterRequest();
        req.setUsername("admin");
        req.setPassword("123456");

        when(userMapper.selectCount(any())).thenReturn(0L);
        when(userMapper.insert(any(User.class))).thenThrow(new DuplicateKeyException("duplicate"));

        assertThatThrownBy(() -> userService.register(req))
                .isInstanceOf(BusinessException.class)
                .extracting("code").isEqualTo(1001);
    }

    @Test
    @DisplayName("登录 - 正常流程")
    void shouldLoginSuccessfully() {
        UserLoginRequest req = new UserLoginRequest();
        req.setUsername("admin");
        req.setPassword("123456");

        User dbUser = new User();
        dbUser.setId(1L);
        dbUser.setUsername("admin");
        dbUser.setPassword(new BCryptPasswordEncoder().encode("123456"));
        dbUser.setNickname("管理员");

        when(userMapper.selectOne(any())).thenReturn(dbUser);

        var result = userService.login(req);

        assertThat(result.getToken()).isEqualTo("mock-jwt-token");
        assertThat(result.getUserId()).isEqualTo(1L);
        assertThat(result.getUsername()).isEqualTo("admin");
    }

    @Test
    @DisplayName("登录 - 密码错误")
    void shouldRejectWrongPassword() {
        UserLoginRequest req = new UserLoginRequest();
        req.setUsername("admin");
        req.setPassword("wrong");

        User dbUser = new User();
        dbUser.setId(1L);
        dbUser.setUsername("admin");
        dbUser.setPassword(new BCryptPasswordEncoder().encode("123456"));

        when(userMapper.selectOne(any())).thenReturn(dbUser);

        assertThatThrownBy(() -> userService.login(req))
                .isInstanceOf(BusinessException.class)
                .extracting("code").isEqualTo(1002);
    }

    @Test
    @DisplayName("登录 - 用户不存在")
    void shouldRejectNonexistentUser() {
        UserLoginRequest req = new UserLoginRequest();
        req.setUsername("ghost");
        req.setPassword("123456");

        when(userMapper.selectOne(any())).thenReturn(null);

        assertThatThrownBy(() -> userService.login(req))
                .isInstanceOf(BusinessException.class)
                .extracting("code").isEqualTo(1002);
    }

    @Test
    @DisplayName("修改资料 - 正常流程")
    void shouldUpdateProfile() {
        User dbUser = new User();
        dbUser.setId(1L);
        dbUser.setUsername("admin");

        when(userMapper.selectById(1L)).thenReturn(dbUser);
        when(userMapper.selectCount(any())).thenReturn(0L);
        when(userMapper.updateById(any(User.class))).thenReturn(1);

        userService.updateProfile(1L, "新昵称", "new@example.com");
    }

    @Test
    @DisplayName("修改密码 - 正常流程")
    void shouldChangePassword() {
        User dbUser = new User();
        dbUser.setId(1L);
        dbUser.setPassword(new BCryptPasswordEncoder().encode("123456"));

        when(userMapper.selectById(1L)).thenReturn(dbUser);
        when(userMapper.updateById(any(User.class))).thenReturn(1);

        userService.changePassword(1L, "123456", "newpass123");
    }

    @Test
    @DisplayName("修改密码 - 原密码错误")
    void shouldRejectWrongOldPassword() {
        User dbUser = new User();
        dbUser.setId(1L);
        dbUser.setPassword(new BCryptPasswordEncoder().encode("123456"));

        when(userMapper.selectById(1L)).thenReturn(dbUser);

        assertThatThrownBy(() -> userService.changePassword(1L, "wrongold", "newpass123"))
                .isInstanceOf(BusinessException.class)
                .extracting("code").isEqualTo(1003);
    }

    @Test
    @DisplayName("登录 - 数据库密码字段为NULL（数据迁移异常场景）")
    void shouldRejectNullPasswordInDB() {
        UserLoginRequest req = new UserLoginRequest();
        req.setUsername("admin");
        req.setPassword("123456");

        User dbUser = new User();
        dbUser.setId(1L);
        dbUser.setUsername("admin");
        dbUser.setPassword(null);

        when(userMapper.selectOne(any())).thenReturn(dbUser);

        assertThatThrownBy(() -> userService.login(req))
                .isInstanceOf(BusinessException.class)
                .extracting("code").isEqualTo(1002);
    }
}
