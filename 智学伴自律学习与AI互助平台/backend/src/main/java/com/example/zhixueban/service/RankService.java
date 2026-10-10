package com.example.zhixueban.service;

import com.example.zhixueban.entity.dto.LeaderboardResponse;

public interface RankService {

    /**
     * 获取指定类型的自律学霸排行榜
     *
     * @param type 榜单类型：day (今日专注) / week (本周自律) / streak (累计打卡) / coins (总学分)
     * @param currentUserId 当前登录学员ID（可空）
     * @return 完整排行榜响应
     */
    LeaderboardResponse getLeaderboard(String type, Long currentUserId);
}
