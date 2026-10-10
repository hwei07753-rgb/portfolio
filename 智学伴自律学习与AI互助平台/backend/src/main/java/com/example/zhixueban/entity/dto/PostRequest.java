package com.example.zhixueban.entity.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 发布社区帖子请求体
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PostRequest {

    /** 分类：求资料/问问题/经验分享/答疑求助 */
    @NotBlank(message = "帖子分类不能为空")
    @Pattern(regexp = "求资料|问问题|经验分享|答疑求助", message = "分类只能是：求资料 / 问问题 / 答疑求助 / 经验分享")
    private String category;

    @NotBlank(message = "标题不能为空")
    @Size(max = 100, message = "标题最多 100 字")
    private String title;

    @NotBlank(message = "内容不能为空")
    @Size(max = 2000, message = "内容最多 2000 字")
    private String content;

    /** 悬赏学分金币（可选，默认 0） */
    private Integer bountyCoins;
}
