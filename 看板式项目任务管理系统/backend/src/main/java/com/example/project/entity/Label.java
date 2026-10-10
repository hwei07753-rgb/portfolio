package com.example.project.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("label")
public class Label {

    @TableId(type = IdType.AUTO)
    private Long id;

    // R-05-issue-4: 已修复 - 添加 @TableField("project_id") 显式声明列名映射,对齐 Task.java/ProjectMember.java 风格
    @TableField("project_id")
    private Long projectId;

    @TableField("name")
    private String name;

    @TableField("color")
    private String color;

    @TableField("create_time")
    private LocalDateTime createTime;

    @TableField("update_time")
    private LocalDateTime updateTime;
}