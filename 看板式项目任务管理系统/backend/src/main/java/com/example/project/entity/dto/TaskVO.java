package com.example.project.entity.dto;

import lombok.Data;

import java.time.LocalDate;
import java.time.LocalDateTime;

import java.util.List;

@Data
public class TaskVO {

    private Long id;
    private Long projectId;
    private String title;
    private String description;
    private String status;
    private String priority;
    private Long assigneeId;
    private String assigneeName;
    private Long creatorId;
    private String creatorName;
    private LocalDate dueDate;
    private Integer orderNo;
    private String blockReason;
    private Integer version;
    private Long milestoneId;
    private LocalDateTime createTime;
    private LocalDateTime updateTime;

    private List<Long> labelIds;
}