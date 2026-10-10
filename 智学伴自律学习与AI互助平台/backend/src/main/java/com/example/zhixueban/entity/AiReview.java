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
 * AI 复盘实体（对齐 ai_review 表，SRS §3.1.3 AI建议 + §3.2.4 AI调用次数统计）
 * 与 checkin 1:1 关系（uk_checkin）
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@TableName("ai_review")
public class AiReview {

    @TableId(type = IdType.AUTO)
    private Long id;

    @TableField("checkin_id")
    private Long checkinId;

    @TableField("user_id")
    private Long userId;

    /** AI 复盘建议内容 */
    @TableField("content")
    private String content;

    /** 生成模型（deepseek/通义/local-template） */
    @TableField("model")
    private String model;

    @TableField("created_at")
    private LocalDateTime createdAt;
}
