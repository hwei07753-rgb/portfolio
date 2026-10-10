package com.example.project.entity.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
public class LabelCreateRequest {

    @NotBlank(message = "请输入标签名")
    @Size(max = 20, message = "标签名不能超过20字符")
    private String name;

    @Pattern(regexp = "^#[0-9A-Fa-f]{6}$", message = "颜色格式需为 #RRGGBB")
    private String color;
}