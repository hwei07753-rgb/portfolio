package com.example.zhixueban.service;

import com.example.zhixueban.entity.dto.CheckinRequest;
import com.example.zhixueban.entity.dto.CheckinVO;

import java.util.List;

/**
 * 每日打卡服务（含 AI 复盘）
 */
public interface CheckinService {

    /** 提交每日打卡并同步生成 AI 复盘建议 */
    CheckinVO submit(Long userId, CheckinRequest request);

    /** 个人历史打卡流水（按时间倒序） */
    List<CheckinVO> myHistory(Long userId);
}
