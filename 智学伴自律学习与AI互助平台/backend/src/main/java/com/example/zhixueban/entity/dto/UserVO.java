package com.example.zhixueban.entity.dto;

import com.example.zhixueban.entity.User;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UserVO {

    private Long id;
    private String openid;
    private String nickname;
    private String avatarUrl;
    private String studyGoal;
    private Integer role;
    private Integer status;
    private LocalDateTime createdAt;

    public static UserVO fromUser(User user) {
        if (user == null) {
            return null;
        }
        return UserVO.builder()
                .id(user.getId())
                .openid(user.getOpenid())
                .nickname(user.getNickname())
                .avatarUrl(user.getAvatarUrl())
                .studyGoal(user.getStudyGoal())
                .role(user.getRole())
                .status(user.getStatus())
                .createdAt(user.getCreatedAt())
                .build();
    }
}
