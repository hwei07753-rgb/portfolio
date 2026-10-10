package com.example.project.entity.dto;

import lombok.Data;

@Data
public class TaskTransitionVO {

    private String fromStatus;
    private String toStatus;
    private Boolean requireOwner;
}
