package com.example.zhixueban.entity.dto;

import com.example.zhixueban.entity.Checkin;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 打卡记录视图对象（含 AI 复盘建议）
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CheckinVO {

    private Long id;
    private String content;
    private String imageUrl;
    /** AI 复盘建议 */
    private String aiReview;
    /** 0=待审核 1=通过 2=删除 */
    private Integer status;
    private LocalDateTime createdAt;

    public static CheckinVO fromEntity(Checkin checkin) {
        return CheckinVO.builder()
                .id(checkin.getId())
                .content(checkin.getContent())
                .imageUrl(checkin.getImageUrl())
                // aiReview 由 Service 从 ai_review 表联查回填（S1b 拆表后）
                .status(checkin.getStatus())
                .createdAt(checkin.getCreatedAt())
                .build();
    }
}
