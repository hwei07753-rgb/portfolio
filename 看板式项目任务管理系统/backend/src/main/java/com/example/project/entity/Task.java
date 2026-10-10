package com.example.project.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.baomidou.mybatisplus.annotation.Version;
import lombok.Data;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("task")
public class Task {

    @TableId(type = IdType.AUTO)
    private Long id;

    @TableField("project_id")
    private Long projectId;

    @TableField("title")
    private String title;

    @TableField("description")
    private String description;

    @TableField("status")
    private String status;

    @TableField("priority")
    private String priority;

    @TableField("assignee_id")
    private Long assigneeId;

    @TableField("creator_id")
    private Long creatorId;

    @TableField("due_date")
    private LocalDate dueDate;

    @TableField("order_no")
    private Integer orderNo;

    @TableField("block_reason")
    private String blockReason;

    @Version
    @TableField("version")
    private Integer version;

    @TableField("milestone_id")
    private Long milestoneId;

    @TableField("create_time")
    private LocalDateTime createTime;

    @TableField("update_time")
    private LocalDateTime updateTime;
}