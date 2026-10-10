package com.example.project.entity.dto;

import lombok.Data;

@Data
public class TaskMilestoneRequest {

    /** Sprint ID，传 null 表示取消 Sprint 关联 */
    private Long milestoneId;
}
