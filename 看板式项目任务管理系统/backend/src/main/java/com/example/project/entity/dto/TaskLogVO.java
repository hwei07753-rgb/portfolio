package com.example.project.entity.dto;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class TaskLogVO {

    private Long id;
    private Long taskId;
    private Long userId;
    private String username;
    private String type;
    private String action;
    private String content;
    private LocalDateTime createTime;
}