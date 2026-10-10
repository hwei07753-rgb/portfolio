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
    /** 是否被采纳为最佳答案（0=否 1=是） */
    private Integer isAccepted;

    public static ReplyVO fromEntity(Reply reply) {
        return ReplyVO.builder()
                .id(reply.getId())
                .postId(reply.getPostId())
                .userId(reply.getUserId())
                .content(reply.getContent())
                .createdAt(reply.getCreatedAt())
                .isAccepted(reply.getIsAccepted() != null ? reply.getIsAccepted() : 0)
                .isAi(false)
                .build();
    }
}
