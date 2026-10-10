package com.example.project.entity.dto;

import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class DependencyCreateRequest {

    @NotNull(message = "前置任务ID不能为空")
    private Long predecessorTaskId;

    @NotNull(message = "后置任务ID不能为空")
    private Long successorTaskId;

    /** 依赖类型，默认 FS */
    private String dependencyType;
}
