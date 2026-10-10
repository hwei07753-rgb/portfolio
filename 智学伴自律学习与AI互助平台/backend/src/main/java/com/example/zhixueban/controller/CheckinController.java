package com.example.zhixueban.controller;

import com.example.zhixueban.common.Result;
import com.example.zhixueban.entity.dto.CheckinRequest;
import com.example.zhixueban.entity.dto.CheckinVO;
import com.example.zhixueban.service.CheckinService;
import com.example.zhixueban.util.UserContext;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 每日打卡模块（对齐 API_DESIGN.md S3 规划）
 */
@RestController
@RequestMapping("/api/checkin")
public class CheckinController {

    private final CheckinService checkinService;

    public CheckinController(CheckinService checkinService) {
        this.checkinService = checkinService;
    }

    /** 提交每日打卡（同步生成 AI 复盘建议） */
    @PostMapping
    public Result<CheckinVO> submit(@Valid @RequestBody CheckinRequest request) {
        CheckinVO vo = checkinService.submit(UserContext.getUserId(), request);
        return Result.success(vo, "打卡成功，AI 复盘已生成");
    }

    /** 个人历史打卡流水 */
    @GetMapping("/my-history")
    public Result<List<CheckinVO>> myHistory() {
        return Result.success(checkinService.myHistory(UserContext.getUserId()));
    }
}
