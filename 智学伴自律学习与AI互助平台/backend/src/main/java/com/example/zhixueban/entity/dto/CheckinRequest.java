package com.example.zhixueban.entity.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 提交每日打卡请求体
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CheckinRequest {

    /** 打卡心得 */
    @NotBlank(message = "打卡心得不能为空")
    @Size(max = 500, message = "打卡心得最多 500 字")
    private String content;

    /** 配图地址（可空） */
    @Size(max = 255, message = "图片地址过长")
    private String imageUrl;
}
