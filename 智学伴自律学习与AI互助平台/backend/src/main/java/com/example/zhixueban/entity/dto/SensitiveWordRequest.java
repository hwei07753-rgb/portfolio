package com.example.zhixueban.entity.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 敏感词新增请求（SRS §6.2.2 敏感词过滤）
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SensitiveWordRequest {

    @NotBlank(message = "敏感词不能为空")
    @Size(max = 50, message = "敏感词长度不能超过 50")
    private String word;
}
