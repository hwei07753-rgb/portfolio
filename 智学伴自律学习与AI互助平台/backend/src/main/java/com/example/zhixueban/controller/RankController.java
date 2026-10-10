package com.example.zhixueban.controller;

import com.example.zhixueban.common.Result;
import com.example.zhixueban.entity.dto.LeaderboardResponse;
import com.example.zhixueban.service.RankService;
import com.example.zhixueban.util.UserContext;
import org.springframework.web.bind.annotation.*;

/**
 * 学霸自律排行榜控制器
 */
@RestController
@RequestMapping("/api/rank")
public class RankController {

    private final RankService rankService;

    public RankController(RankService rankService) {
        this.rankService = rankService;
    }

    /**
     * 查询排行榜数据
     *
     * @param type 榜单类型：day (今日专注榜) / week (本周自律榜) / streak (打卡英雄榜) / coins (学分风云榜)
     * @return 排行榜前列学员及自身位次
     */
    @GetMapping("/leaderboard")
    public Result<LeaderboardResponse> getLeaderboard(@RequestParam(value = "type", defaultValue = "day") String type) {
        Long currentUserId = UserContext.getUserId();
        LeaderboardResponse response = rankService.getLeaderboard(type, currentUserId);
        return Result.success(response);
    }
}
