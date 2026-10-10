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
 * 后台管理员实体（对齐 admin 表）
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@TableName("admin")
public class Admin {

    @TableId(type = IdType.AUTO)
    private Long id;

    @TableField("username")
    private String username;

    /** 密码 BCrypt 加密存储，禁止明文 */
    @TableField("password")
    private String password;

    @TableField("nickname")
    private String nickname;

    /** 1=正常 0=禁用 */
    @TableField("status")
    private Integer status;

    @TableField("created_at")
    private LocalDateTime createdAt;

    @TableField("updated_at")
    private LocalDateTime updatedAt;
}
