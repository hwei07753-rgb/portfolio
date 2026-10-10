package com.example.zhixueban.entity.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 保存单次专注记录请求体
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class FocusRecordRequest {

    /** 专注时长（分钟），1~180 */
    @NotNull(message = "专注时长不能为空")
    @Min(value = 1, message = "专注时长至少 1 分钟")
    @Max(value = 180, message = "专注时长最多 180 分钟")
    private Integer durationMinutes;

    /** 专注标签（背单词/刷题/看网课等），可空 */
    private String tag;

    /** 0=完成 1=放弃，默认 0 */
    private Integer status;

    /** 开始时间（可空，默认 当前时间-时长） */
    @com.fasterxml.jackson.annotation.JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime startTime;

    /** 结束时间（可空，默认 当前时间） */
    @com.fasterxml.jackson.annotation.JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime endTime;
}
