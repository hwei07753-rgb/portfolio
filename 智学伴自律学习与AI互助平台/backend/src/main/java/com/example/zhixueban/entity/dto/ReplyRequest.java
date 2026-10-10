package com.example.zhixueban.entity.dto;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 发表回复请求体
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ReplyRequest {

    @NotNull(message = "帖子 ID 不能为空")
    private Long postId;

    @jakarta.validation.constraints.NotBlank(message = "回复内容不能为空")
    @Size(max = 500, message = "回复内容最多 500 字")
    private String content;
}
