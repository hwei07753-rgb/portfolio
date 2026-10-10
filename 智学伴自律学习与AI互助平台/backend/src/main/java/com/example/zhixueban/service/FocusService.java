package com.example.zhixueban.service;

import com.example.zhixueban.entity.FocusTag;
import com.example.zhixueban.entity.dto.FocusRecordRequest;
import com.example.zhixueban.entity.dto.FocusRecordVO;
import com.example.zhixueban.entity.dto.TodayStatsResponse;

import java.util.List;

/**
 * 番茄钟专注服务
 */
public interface FocusService {

    /** 保存单次专注记录 */
    FocusRecordVO record(Long userId, FocusRecordRequest request);

    /** 今日专注数据看板 */
    TodayStatsResponse todayStats(Long userId);

    /** 今日专注流水（按开始时间倒序） */
    List<FocusRecordVO> todayList(Long userId);

    /** 专注标签字典（启用中，按 sort 升序，SRS §3.1.2） */
    List<FocusTag> listTags();
}
