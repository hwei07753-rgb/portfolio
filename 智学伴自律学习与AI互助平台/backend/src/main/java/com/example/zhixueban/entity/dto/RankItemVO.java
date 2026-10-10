package com.example.zhixueban.entity.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 排行榜单项数据传输对象
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RankItemVO {

    /** 排名序号（1, 2, 3...） */
    private Integer rank;

    /** 学员ID */
    private Long userId;

    /** 学员昵称 */
    private String nickname;

    /** 头像URL */
    private String avatarUrl;

    /** 学习目标方向 */
    private String studyGoal;

    /** 排行得分（分钟数 / 打卡天数 / 金币分值） */
    private Integer score;

    /** 格式化得分显示（如 "120 分钟", "18 天", "350 币"） */
    private String scoreFormatted;

    /** 是否为当前登录用户本人 */
    private Boolean isSelf;
}
