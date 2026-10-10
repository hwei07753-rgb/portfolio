package com.example.zhixueban.entity.dto;

import com.example.zhixueban.entity.FocusRecord;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 专注记录视图对象（返回给前端）
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class FocusRecordVO {

    private Long id;
    private Integer durationMinutes;
    private String tag;
    /** 0=完成 1=放弃 */
    private Integer status;
    private LocalDateTime startTime;
    private LocalDateTime endTime;

    public static FocusRecordVO fromEntity(FocusRecord record) {
        return FocusRecordVO.builder()
                .id(record.getId())
                .durationMinutes(record.getDurationMinutes())
                .tag(record.getTag())
                .status(record.getStatus())
                .startTime(record.getStartTime())
                .endTime(record.getEndTime())
                .build();
    }
}
