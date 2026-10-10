package com.example.zhixueban.entity.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 后台审核：帖子列表视图（SRS §3.2.3 内容审核）
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AdminPostVO {

    private Long id;
    private Long userId;
    private String userNickname;
    private String category;
    private String title;
    private String content;
    /** 0=待审核 1=通过 2=删除 */
    private Integer status;
    private LocalDateTime createdAt;
}
