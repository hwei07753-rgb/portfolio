package com.example.project.entity.dto;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class TaskDependencyVO {

    private Long id;
    private Long projectId;
    private Long predecessorTaskId;
    private Long successorTaskId;
    private String dependencyType;
    private LocalDateTime createTime;
}
