package com.example.zhixueban.entity.dto;

import com.example.zhixueban.entity.User;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 管理员后台：用户列表展示对象（openid 脱敏）
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AdminUserVO {

    private Long id;
    private String openid;
    private String nickname;
    private Integer role;
    private Integer status;
    private LocalDateTime createdAt;

    public static AdminUserVO fromUser(User user) {
        if (user == null) {
            return null;
        }
        return AdminUserVO.builder()
                .id(user.getId())
                .openid(maskOpenid(user.getOpenid()))
                .nickname(user.getNickname())
                .role(user.getRole())
                .status(user.getStatus())
                .createdAt(user.getCreatedAt())
                .build();
    }

    /**
     * openid 脱敏：保留前 6 位与后 4 位，中间用 * 代替
     */
    private static String maskOpenid(String openid) {
        if (openid == null || openid.length() <= 10) {
            return openid;
        }
        return openid.substring(0, 6) + "****" + openid.substring(openid.length() - 4);
    }
}
