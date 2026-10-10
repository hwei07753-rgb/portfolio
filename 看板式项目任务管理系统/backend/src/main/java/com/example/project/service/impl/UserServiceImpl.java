package com.example.project.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.example.project.common.BusinessException;
import com.example.project.entity.User;
import com.example.project.entity.dto.UserLoginRequest;
import com.example.project.entity.dto.UserLoginResponse;
import com.example.project.entity.dto.UserRegisterRequest;
import com.example.project.mapper.UserMapper;
import com.example.project.service.UserService;
import com.example.project.util.JwtUtils;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class UserServiceImpl extends ServiceImpl<UserMapper, User> implements UserService {

    private final JwtUtils jwtUtils;
    // R-05-issue-6: 已修复 - 教学简化保留new初始化（功能正确，不需额外@Bean配置类；仅spring-security-crypto子模块无自动配置）
    private final BCryptPasswordEncoder passwordEncoder = new BCryptPasswordEncoder();

    // R-05-issue-1: 已修复 - insert外套try-catch捕获DuplicateKeyException→BusinessException(1001)，并发注册时友好提示"用户名已存在"而非500
    @Override
    @Transactional
    public User register(UserRegisterRequest request) {
        Long count = baseMapper.selectCount(
                new LambdaQueryWrapper<User>().eq(User::getUsername, request.getUsername()));
        if (count > 0) {
            throw new BusinessException(1001, "用户名已存在");
        }

        User user = new User();
        user.setUsername(request.getUsername());
        user.setPassword(passwordEncoder.encode(request.getPassword()));
        try {
            baseMapper.insert(user);
        } catch (DuplicateKeyException e) {
            throw new BusinessException(1001, "用户名已存在");
        }
        log.info("用户注册成功: username={}", request.getUsername());
        user.setPassword(null);
        return user;
    }

    @Override
    public UserLoginResponse login(UserLoginRequest request) {
        User user = getByUsernameWithPassword(request.getUsername());
        if (user == null) {
            throw new BusinessException(1002, "用户名或密码错误");
        }
        // D-05-fix-2026-05-18: 增加user.getPassword()空值防御,防止DB密码字段为null时BCryptPasswordEncoder.matches()抛NPE→500
        if (user.getPassword() == null) {
            log.error("用户密码字段为null: userId={}", user.getId());
            throw new BusinessException(1002, "用户名或密码错误");
        }
        if (!passwordEncoder.matches(request.getPassword(), user.getPassword())) {
            throw new BusinessException(1002, "用户名或密码错误");
        }

        String token = jwtUtils.generateToken(user.getId());
        log.info("用户登录成功: username={}", request.getUsername());
        return new UserLoginResponse(token, user.getId(), user.getUsername(), user.getNickname());
    }

    @Override
    public User getByUsernameWithPassword(String username) {
        LambdaQueryWrapper<User> wrapper = new LambdaQueryWrapper<User>()
                .eq(User::getUsername, username);
        return baseMapper.selectOne(wrapper);
    }

    @Override
    public List<User> searchByUsername(String keyword) {
        LambdaQueryWrapper<User> wrapper = new LambdaQueryWrapper<User>()
                .eq(User::getUsername, keyword);
        return baseMapper.selectList(wrapper);
    }

    // R-05-issue-7: 已修复 - updateProfile方法加@Transactional，read-check-write(email唯一性检查→更新)在同一事务内执行
    @Override
    @Transactional
    public void updateProfile(Long userId, String nickname, String email) {
        User user = baseMapper.selectById(userId);
        // R-05-issue-10: 已修复 - 错误码改为1005=用户不存在，避免与API_DESIGN §4.3中1004="token无效"语义冲突
        if (user == null) {
            throw new BusinessException(1005, "用户不存在");
        }
        if (email != null && !email.isBlank()) {
            Long count = baseMapper.selectCount(
                    new LambdaQueryWrapper<User>()
                            .eq(User::getEmail, email)
                            .ne(User::getId, userId));
            if (count > 0) {
                throw new BusinessException(1001, "该邮箱已被占用");
            }
        }
        User update = new User();
        update.setId(userId);
        update.setNickname(nickname != null && nickname.isBlank() ? null : nickname);
        update.setEmail(email != null && email.isBlank() ? null : email);
        // R-05-issue-8: 已修复 - updateById外套try-catch DuplicateKeyException，并发邮箱冲突时友好提示"该邮箱已被占用"而非500
        try {
            baseMapper.updateById(update);
        } catch (DuplicateKeyException e) {
            throw new BusinessException(1001, "该邮箱已被占用");
        }
        log.info("用户资料更新成功: userId={}", userId);
    }

    // R-05-issue-9: 已修复 - changePassword写操作方法加@Transactional
    @Override
    @Transactional
    public void changePassword(Long userId, String oldPassword, String newPassword) {
        User user = baseMapper.selectById(userId);
        // R-05-issue-10: 已修复 - 错误码改为1005=用户不存在
        if (user == null) {
            throw new BusinessException(1005, "用户不存在");
        }
        if (user.getPassword() == null || !passwordEncoder.matches(oldPassword, user.getPassword())) {
            throw new BusinessException(1003, "原密码不正确");
        }
        User update = new User();
        update.setId(userId);
        update.setPassword(passwordEncoder.encode(newPassword));
        baseMapper.updateById(update);
        log.info("用户密码修改成功: userId={}", userId);
    }
}