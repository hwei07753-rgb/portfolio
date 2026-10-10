package com.example.project.entity.dto;

import lombok.AllArgsConstructor;
import lombok.Data;

@Data
@AllArgsConstructor
public class UserLoginResponse {

    private String token;
    private Long userId;
    private String username;
    private String nickname;
}