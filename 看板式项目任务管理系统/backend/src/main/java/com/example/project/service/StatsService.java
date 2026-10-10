package com.example.project.service;

import com.example.project.entity.dto.BurndownPoint;

import java.util.List;
import java.util.Map;

public interface StatsService {

    /** 按状态统计项目内任务数量（排除已删除），空项目返回全零 Map */
    Map<String, Integer> getStatusStats(Long projectId, Long userId);

    /** 燃尽图数据点。传 milestoneId 时基于 Sprint 起止日期精确计算；不传时基于 create_time 推算 */
    List<BurndownPoint> getBurndown(Long projectId, Long userId, Long milestoneId);
}