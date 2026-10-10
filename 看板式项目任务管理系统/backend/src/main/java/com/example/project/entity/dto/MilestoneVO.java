package com.example.project.entity.dto;

import lombok.Data;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
public class MilestoneVO {

    private Long id;

    private String name;

    private LocalDate startDate;

    private LocalDate endDate;

    /** Sprint状态：upcoming(未开始) / active(进行中) / completed(已结束) · 由日期自动推断不存DB */
    private String status;

    private Integer taskCount;

    private LocalDateTime createTime;
}
