package com.example.zhixueban.entity.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 排行榜完整响应对象
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class LeaderboardResponse {

    /** 榜单类型：day (今日专注) / week (本周自律) / streak (打卡英雄) / coins (总学分) */
    private String type;

    /** 榜单中文标题 */
    private String typeName;

    /** 排行榜前 10 或 20 强列表 */
    private List<RankItemVO> topList;

    /** 当前登录学员自身排行信息 */
    private RankItemVO myRank;

    /** 距离上一名的分差（为0代表榜首或暂无差距） */
    private Integer gapToAbove;

    /** 榜单动态激励语录 */
    private String motivationText;
}
