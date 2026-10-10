package com.example.project.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("task_transition")
public class TaskTransition {

    @TableId(type = IdType.AUTO)
    private Long id;

    @TableField("from_status")
    private String fromStatus;

    @TableField("to_status")
    private String toStatus;

    @TableField("require_owner")
    private Integer requireOwner;

    @TableField("create_time")
    private LocalDateTime createTime;
}
