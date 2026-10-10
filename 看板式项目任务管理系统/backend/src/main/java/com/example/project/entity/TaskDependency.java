package com.example.project.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("task_dependency")
public class TaskDependency {

    @TableId(type = IdType.AUTO)
    private Long id;

    @TableField("project_id")
    private Long projectId;

    @TableField("predecessor_task_id")
    private Long predecessorTaskId;

    @TableField("successor_task_id")
    private Long successorTaskId;

    @TableField("dependency_type")
    private String dependencyType;

    @TableField("create_time")
    private LocalDateTime createTime;
}
