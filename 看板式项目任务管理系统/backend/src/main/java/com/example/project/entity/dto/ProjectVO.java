package com.example.project.entity.dto;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class ProjectVO {

    private Long id;
    private String name;
    private Long ownerId;
    private String ownerName;
    private Boolean archived;
    private Integer memberCount;
    private Integer taskCount;
    private String myRole;
    private LocalDateTime createTime;
    private LocalDateTime updateTime;
}