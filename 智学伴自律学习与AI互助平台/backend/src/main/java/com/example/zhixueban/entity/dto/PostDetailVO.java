package com.example.zhixueban.entity.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 帖子详情视图（帖子 + 回复列表）
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PostDetailVO {

    private PostVO post;
    private List<ReplyVO> replies;
}
