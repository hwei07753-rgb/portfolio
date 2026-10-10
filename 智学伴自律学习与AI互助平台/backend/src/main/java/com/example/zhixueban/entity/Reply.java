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
 * 帖子回复实体类（对齐 reply 表）
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@TableName("reply")
public class Reply {

    @TableId(type = IdType.AUTO)
    private Long id;

    @TableField("post_id")
    private Long postId;

    @TableField("user_id")
    private Long userId;

    @TableField("content")
    private String content;

    @TableField("created_at")
    private LocalDateTime createdAt;

    /**
     * 是否被采纳为最佳答案（0=未采纳 1=已采纳）
     */
    @TableField("is_accepted")
    private Integer isAccepted;
}
