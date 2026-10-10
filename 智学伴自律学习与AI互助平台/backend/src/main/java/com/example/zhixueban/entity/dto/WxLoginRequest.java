package com.example.zhixueban.entity.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class WxLoginRequest {

    @NotBlank(message = "微信授权 code 不能为空")
    private String code;
}
