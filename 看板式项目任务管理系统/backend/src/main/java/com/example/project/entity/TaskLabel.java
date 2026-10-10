package com.example.project.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("task_label")
public class TaskLabel {

    @TableId(type = IdType.AUTO)
    private Long id;

    // R-05-issue-5: 已修复 - 添加 @TableField 显式声明列名映射,对齐 Task.java/ProjectMember.java 风格
    @TableField("task_id")
    private Long taskId;

    @TableField("label_id")
    private Long labelId;

    @TableField("create_time")
    private LocalDateTime createTime;
}