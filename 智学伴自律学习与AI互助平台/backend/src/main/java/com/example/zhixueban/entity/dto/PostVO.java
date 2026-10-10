package com.example.zhixueban.entity.dto;

import com.example.zhixueban.entity.Post;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 帖子视图对象（广场列表 / 帖子详情）
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PostVO {

    private Long id;
    private Long userId;
    /** 分类：求资料/问问题/经验分享 */
    private String category;
    private String title;
    private String content;
    /** 0=待审核 1=通过 2=删除 */
    private Integer status;
    private LocalDateTime createdAt;
    /** 作者昵称 */
    private String authorNickname;
    /** 回复数 */
    private Integer replyCount;

    public static PostVO fromEntity(Post post) {
        return PostVO.builder()
                .id(post.getId())
                .userId(post.getUserId())
                .category(post.getCategory())
                .title(post.getTitle())
                .content(post.getContent())
                .status(post.getStatus())
                .createdAt(post.getCreatedAt())
                .replyCount(0)
                .build();
    }
}
