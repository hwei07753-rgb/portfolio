package com.example.zhixueban.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 专注标签字典实体（对齐 focus_tag 表，SRS §3.1.2 番茄钟标签规范化）
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@TableName("focus_tag")
public class FocusTag {

    @TableId(type = IdType.AUTO)
    private Long id;

    @TableField("name")
    private String name;

    /** 图标（emoji） */
    @TableField("icon")
    private String icon;

    /** 排序值（小在前） */
    @TableField("sort")
    private Integer sort;

    /** 1=启用 0=停用 */
    @TableField("status")
    private Integer status;
}
