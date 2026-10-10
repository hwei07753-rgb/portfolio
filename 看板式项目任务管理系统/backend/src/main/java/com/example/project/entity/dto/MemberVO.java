package com.example.project.entity.dto;

import lombok.Data;

@Data
public class MemberVO {

    private Long userId;
    private String username;
    private String nickname;
    private String role;
}