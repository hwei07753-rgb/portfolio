package com.example.zhixueban.entity.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 后台审核：打卡列表视图（SRS §3.2.3 内容审核）
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AdminCheckinVO {

    private Long id;
    private Long userId;
    private String userNickname;
    private String content;
    private String imageUrl;
    /** AI 复盘建议（从 ai_review 表联查） */
    private String aiReview;
    /** 0=待审核 1=通过 2=删除 */
    private Integer status;
    private LocalDateTime createdAt;
}
