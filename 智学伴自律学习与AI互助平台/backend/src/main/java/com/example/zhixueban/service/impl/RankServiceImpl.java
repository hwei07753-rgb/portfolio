package com.example.zhixueban.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.example.zhixueban.entity.User;
import com.example.zhixueban.entity.dto.LeaderboardResponse;
import com.example.zhixueban.entity.dto.RankItemVO;
import com.example.zhixueban.mapper.CheckinMapper;
import com.example.zhixueban.mapper.FocusRecordMapper;
import com.example.zhixueban.mapper.UserMapper;
import com.example.zhixueban.service.RankService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.temporal.TemporalAdjusters;
import java.util.*;

@Slf4j
@Service
public class RankServiceImpl implements RankService {

    private final FocusRecordMapper focusRecordMapper;
    private final CheckinMapper checkinMapper;
    private final UserMapper userMapper;

    public RankServiceImpl(FocusRecordMapper focusRecordMapper,
                           CheckinMapper checkinMapper,
                           UserMapper userMapper) {
        this.focusRecordMapper = focusRecordMapper;
        this.checkinMapper = checkinMapper;
        this.userMapper = userMapper;
    }

    @Override
    public LeaderboardResponse getLeaderboard(String type, Long currentUserId) {
        String safeType = (type == null || type.isBlank()) ? "day" : type.trim().toLowerCase();

        String typeName;
        String unit;
        List<RankItemVO> topList = new ArrayList<>();
        RankItemVO myRank = null;
        Integer gapToAbove = 0;

        switch (safeType) {
            case "week" -> {
                typeName = "本周自律榜";
                unit = "分钟";
                LocalDateTime weekStart = LocalDate.now().with(TemporalAdjusters.previousOrSame(DayOfWeek.MONDAY)).atStartOfDay();
                LocalDateTime now = LocalDateTime.now();

                List<Map<String, Object>> records = focusRecordMapper.sumDurationByUser(weekStart, now, 20);
                topList = buildRankListFromAgg(records, unit, currentUserId);

                if (currentUserId != null) {
                    myRank = findOrComputeSelfRank(topList, currentUserId, () -> {
                        Integer score = focusRecordMapper.sumDurationForUser(currentUserId, weekStart, now);
                        return score != null ? score : 0;
                    }, unit);
                }
            }
            case "streak", "checkin" -> {
                typeName = "打卡英雄榜";
                unit = "天";

                List<Map<String, Object>> records = checkinMapper.countCheckinByUser(20);
                topList = buildRankListFromAgg(records, unit, currentUserId);

                if (currentUserId != null) {
                    myRank = findOrComputeSelfRank(topList, currentUserId, () -> {
                        Integer score = checkinMapper.countCheckinForUser(currentUserId);
                        return score != null ? score : 0;
                    }, unit);
                }
            }
            case "coins" -> {
                typeName = "学分风云榜";
                unit = "币";

                List<User> users = userMapper.selectList(new LambdaQueryWrapper<User>()
                        .eq(User::getStatus, 0)
                        .eq(User::getRole, 0)
                        .orderByDesc(User::getCoins)
                        .last("LIMIT 20"));

                int r = 1;
                for (User u : users) {
                    int score = u.getCoins() != null ? u.getCoins() : 0;
                    boolean isSelf = currentUserId != null && currentUserId.equals(u.getId());
                    RankItemVO item = RankItemVO.builder()
                            .rank(r++)
                            .userId(u.getId())
                            .nickname(u.getNickname())
                            .avatarUrl(u.getAvatarUrl())
                            .studyGoal(u.getStudyGoal())
                            .score(score)
                            .scoreFormatted(score + " " + unit)
                            .isSelf(isSelf)
                            .build();
                    topList.add(item);
                    if (isSelf) {
                        myRank = item;
                    }
                }

                if (currentUserId != null && myRank == null) {
                    User self = userMapper.selectById(currentUserId);
                    if (self != null) {
                        int score = self.getCoins() != null ? self.getCoins() : 0;
                        Long higherCount = userMapper.selectCount(new LambdaQueryWrapper<User>()
                                .eq(User::getStatus, 0)
                                .eq(User::getRole, 0)
                                .gt(User::getCoins, score));
                        int estimatedRank = (higherCount != null ? higherCount.intValue() : 0) + 1;
                        myRank = RankItemVO.builder()
                                .rank(estimatedRank)
                                .userId(self.getId())
                                .nickname(self.getNickname())
                                .avatarUrl(self.getAvatarUrl())
                                .studyGoal(self.getStudyGoal())
                                .score(score)
                                .scoreFormatted(score + " " + unit)
                                .isSelf(true)
                                .build();
                    }
                }
            }
            default -> { // "day" (默认今日专注榜)
                safeType = "day";
                typeName = "今日专注榜";
                unit = "分钟";
                LocalDateTime dayStart = LocalDate.now().atStartOfDay();
                LocalDateTime dayEnd = LocalDate.now().atTime(LocalTime.MAX);

                List<Map<String, Object>> records = focusRecordMapper.sumDurationByUser(dayStart, dayEnd, 20);
                topList = buildRankListFromAgg(records, unit, currentUserId);

                if (currentUserId != null) {
                    myRank = findOrComputeSelfRank(topList, currentUserId, () -> {
                        Integer score = focusRecordMapper.sumDurationForUser(currentUserId, dayStart, dayEnd);
                        return score != null ? score : 0;
                    }, unit);
                }
            }
        }

        // 计算距离上一名的分差与激励语录
        if (myRank != null && myRank.getRank() != null) {
            int rankNum = myRank.getRank();
            if (rankNum > 1) {
                if (rankNum - 2 < topList.size()) {
                    gapToAbove = Math.max(0, topList.get(rankNum - 2).getScore() - myRank.getScore());
                } else if (!topList.isEmpty()) {
                    gapToAbove = Math.max(0, topList.get(topList.size() - 1).getScore() - myRank.getScore());
                }
            }
        }

        String motivationText = buildMotivationText(myRank, gapToAbove, unit);

        return LeaderboardResponse.builder()
                .type(safeType)
                .typeName(typeName)
                .topList(topList)
                .myRank(myRank)
                .gapToAbove(gapToAbove)
                .motivationText(motivationText)
                .build();
    }

    private List<RankItemVO> buildRankListFromAgg(List<Map<String, Object>> records, String unit, Long currentUserId) {
        List<RankItemVO> result = new ArrayList<>();
        if (records == null || records.isEmpty()) {
            return result;
        }

        // 收集所有 userId 批量查询用户信息
        Set<Long> userIds = new HashSet<>();
        for (Map<String, Object> map : records) {
            Object uidObj = map.get("userId");
            if (uidObj != null) {
                userIds.add(Long.valueOf(uidObj.toString()));
            }
        }

        Map<Long, User> userMap = new HashMap<>();
        if (!userIds.isEmpty()) {
            List<User> users = userMapper.selectBatchIds(userIds);
            for (User u : users) {
                userMap.put(u.getId(), u);
            }
        }

        int rank = 1;
        for (Map<String, Object> map : records) {
            Object uidObj = map.get("userId");
            if (uidObj == null) continue;
            Long uid = Long.valueOf(uidObj.toString());
            User u = userMap.get(uid);

            int score = 0;
            Object scoreObj = map.get("totalScore");
            if (scoreObj instanceof Number n) {
                score = n.intValue();
            }

            boolean isSelf = currentUserId != null && currentUserId.equals(uid);
            RankItemVO item = RankItemVO.builder()
                    .rank(rank++)
                    .userId(uid)
                    .nickname(u != null ? u.getNickname() : "自律研友")
                    .avatarUrl(u != null ? u.getAvatarUrl() : null)
                    .studyGoal(u != null ? u.getStudyGoal() : null)
                    .score(score)
                    .scoreFormatted(score + " " + unit)
                    .isSelf(isSelf)
                    .build();
            result.add(item);
        }
        return result;
    }

    private RankItemVO findOrComputeSelfRank(List<RankItemVO> topList, Long currentUserId, java.util.function.Supplier<Integer> scoreSupplier, String unit) {
        for (RankItemVO item : topList) {
            if (currentUserId.equals(item.getUserId())) {
                return item;
            }
        }
        // 不在前 20 名，单独组装个人排位信息
        User self = userMapper.selectById(currentUserId);
        if (self == null) {
            return null;
        }
        int score = scoreSupplier.get();
        int rank = topList.size() + 1; // 估算名次
        return RankItemVO.builder()
                .rank(rank)
                .userId(self.getId())
                .nickname(self.getNickname())
                .avatarUrl(self.getAvatarUrl())
                .studyGoal(self.getStudyGoal())
                .score(score)
                .scoreFormatted(score + " " + unit)
                .isSelf(true)
                .build();
    }

    private String buildMotivationText(RankItemVO myRank, Integer gap, String unit) {
        if (myRank == null || myRank.getRank() == null) {
            return "🌱 所谓自由，不是随心所欲，而是自我主宰。开启一段专注，登上自律荣誉榜！";
        }
        int r = myRank.getRank();
        if (r == 1) {
            return "👑 傲视群雄！当前位列榜首，自律之光闪耀全场，继续领跑！";
        }
        if (r <= 3) {
            return String.format("🔥 稳坐前三甲！距上一名仅差 %d %s，冲刺金牌宝座！", gap, unit);
        }
        if (r <= 10) {
            return String.format("💪 跻身学霸十强圈！距上一名仅差 %d %s，保持冲刺势头！", gap, unit);
        }
        return String.format("🌟 笃行致远，不负韶华！距上一名仅差 %d %s，一个番茄钟即可实现反超！", gap, unit);
    }
}
