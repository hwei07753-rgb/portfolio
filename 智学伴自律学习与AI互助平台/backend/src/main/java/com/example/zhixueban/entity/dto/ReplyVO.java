package com.example.zhixueban.entity.dto;

import com.example.zhixueban.entity.Reply;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 回复视图对象
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ReplyVO {

    private Long id;
    private Long postId;
    private Long userId;
    private String content;
    private LocalDateTime createdAt;
    /** 回复者昵称 */
    private String authorNickname;
    /** 是否为 AI 助教答疑 */
    private Boolean isAi;

    public static ReplyVO fromEntity(Reply reply) {
        return ReplyVO.builder()
                .id(reply.getId())
                .postId(reply.getPostId())
                .userId(reply.getUserId())
                .content(reply.getContent())
                .createdAt(reply.getCreatedAt())
                .isAi(false)
                .build();
    }
}
