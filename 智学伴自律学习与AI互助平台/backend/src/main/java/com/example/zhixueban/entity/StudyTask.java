package com.example.zhixueban.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 每日学业任务清单项实体类（对齐 study_task 表）
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@TableName("study_task")
public class StudyTask {

    @TableId(type = IdType.AUTO)
    private Long id;

    @TableField("plan_id")
    private Long planId;

    @TableField("user_id")
    private Long userId;

    @TableField("title")
    private String title;

    @TableField("reward_coins")
    private Integer rewardCoins;

    /**
     * 0=今日未完成 1=今日已完成
     */
    @TableField("is_completed")
    private Integer isCompleted;

    @TableField("completed_at")
    private LocalDateTime completedAt;

    @TableField("continuous_days")
    private Integer continuousDays;

    @TableField("created_at")
    private LocalDateTime createdAt;
}
