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
 * 社区帖子实体类（对齐 post 表）
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@TableName("post")
public class Post {

    @TableId(type = IdType.AUTO)
    private Long id;

    @TableField("user_id")
    private Long userId;

    @TableField("category")
    private String category;

    @TableField("title")
    private String title;

    @TableField("content")
    private String content;

    /**
     * 0=待审核 1=通过 2=删除
     */
    @TableField("status")
    private Integer status;

    @TableField("created_at")
    private LocalDateTime createdAt;

    /**
     * 悬赏金币（0表示无悬赏）
     */
    @TableField("bounty_coins")
    private Integer bountyCoins;

    /**
     * 是否已解决（0=未解决 1=已解决）
     */
    @TableField("is_solved")
    private Integer isSolved;

    /**
     * 采纳的最佳答案回复ID
     */
    @TableField("accepted_reply_id")
    private Long acceptedReplyId;
}
