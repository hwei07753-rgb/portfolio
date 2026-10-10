package com.example.zhixueban.controller;

import com.example.zhixueban.common.Result;
import com.example.zhixueban.entity.FocusTag;
import com.example.zhixueban.entity.dto.FocusRecordRequest;
import com.example.zhixueban.entity.dto.FocusRecordVO;
import com.example.zhixueban.entity.dto.TodayStatsResponse;
import com.example.zhixueban.service.FocusService;
import com.example.zhixueban.util.UserContext;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 番茄钟专注模块（对齐 API_DESIGN.md S3 规划）
 */
@RestController
@RequestMapping("/api/focus")
public class FocusController {

    private final FocusService focusService;

    public FocusController(FocusService focusService) {
        this.focusService = focusService;
    }

    /** 保存单次专注记录（完成/放弃） */
    @PostMapping("/record")
    public Result<FocusRecordVO> record(@Valid @RequestBody FocusRecordRequest request) {
        return Result.success(focusService.record(UserContext.getUserId(), request), "专注记录已保存");
    }

    /** 今日专注数据看板 */
    @GetMapping("/today-stats")
    public Result<TodayStatsResponse> todayStats() {
        return Result.success(focusService.todayStats(UserContext.getUserId()));
    }

    /** 今日专注流水记录 */
    @GetMapping("/today-list")
    public Result<List<FocusRecordVO>> todayList() {
        return Result.success(focusService.todayList(UserContext.getUserId()));
    }

    /** 专注标签字典（SRS §3.1.2 番茄钟标签规范化） */
    @GetMapping("/tags")
    public Result<List<FocusTag>> tags() {
        return Result.success(focusService.listTags());
    }
}
