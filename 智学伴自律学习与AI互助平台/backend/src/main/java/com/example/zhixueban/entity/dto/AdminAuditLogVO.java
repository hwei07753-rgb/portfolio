package com.example.zhixueban.entity.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 后台：审核记录视图（audit_log 留痕查询）
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AdminAuditLogVO {

    private Long id;
    /** 1=打卡 2=帖子 */
    private Integer bizType;
    private Long bizId;
    private Long adminId;
    private String adminName;
    /** 1=通过 2=删除 */
    private Integer action;
    private String reason;
    private LocalDateTime createdAt;
}
