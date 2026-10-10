package com.example.zhixueban.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 内容审核记录实体（对齐 audit_log 表，SRS §3.2.3 审核留痕）
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@TableName("audit_log")
public class AuditLog {

    @TableId(type = IdType.AUTO)
    private Long id;

    /** 审核对象类型 1=打卡 2=帖子 */
    @TableField("biz_type")
    private Integer bizType;

    /** 业务ID（打卡ID/帖子ID） */
    @TableField("biz_id")
    private Long bizId;

    /** 操作管理员ID */
    @TableField("admin_id")
    private Long adminId;

    /** 审核动作 1=通过 2=删除 */
    @TableField("action")
    private Integer action;

    /** 删除/驳回原因（可空） */
    @TableField("reason")
    private String reason;

    @TableField("created_at")
    private LocalDateTime createdAt;
}
