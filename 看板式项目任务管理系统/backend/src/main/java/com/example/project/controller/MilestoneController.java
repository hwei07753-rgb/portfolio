package com.example.project.controller;

import com.example.project.common.Result;
import com.example.project.entity.dto.MilestoneCreateRequest;
import com.example.project.entity.dto.MilestoneVO;
import com.example.project.service.MilestoneService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestAttribute;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequiredArgsConstructor
public class MilestoneController {

    private final MilestoneService milestoneService;

    /** Sprint 列表（全量返回不分页） */
    @GetMapping("/api/projects/{projectId}/milestones")
    public Result<List<MilestoneVO>> list(
            @PathVariable Long projectId,
            @RequestAttribute("userId") Long userId) {
        List<MilestoneVO> list = milestoneService.listMilestones(projectId, userId);
        return Result.success(list);
    }

    /** 创建 Sprint（仅 owner） */
    @PostMapping("/api/projects/{projectId}/milestones")
    public Result<MilestoneVO> create(
            @PathVariable Long projectId,
            @RequestBody @Valid MilestoneCreateRequest request,
            @RequestAttribute("userId") Long userId) {
        MilestoneVO vo = milestoneService.createMilestone(projectId, request, userId);
        return Result.success(vo, "Sprint 创建成功");
    }

    /** 删除 Sprint + 解关联任务（仅 owner） */
    @DeleteMapping("/api/projects/{projectId}/milestones/{id}")
    public Result<Void> delete(
            @PathVariable Long projectId,
            @PathVariable Long id,
            @RequestAttribute("userId") Long userId) {
        milestoneService.deleteMilestone(projectId, id, userId);
        return Result.success(null, "Sprint 已删除");
    }
}
