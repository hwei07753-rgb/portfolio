package com.example.project.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.example.project.entity.Milestone;
import com.example.project.entity.dto.MilestoneCreateRequest;
import com.example.project.entity.dto.MilestoneVO;

import java.util.List;

public interface MilestoneService extends IService<Milestone> {

    /** 查询项目内所有 Sprint 列表（全量返回不分页，含状态自动推断 + 任务数） */
    List<MilestoneVO> listMilestones(Long projectId, Long userId);

    /** 创建 Sprint（仅 owner） */
    MilestoneVO createMilestone(Long projectId, MilestoneCreateRequest request, Long userId);

    /** 删除 Sprint + 将关联任务的 milestone_id 设为 NULL（SET NULL 外键）· 仅 owner */
    void deleteMilestone(Long projectId, Long milestoneId, Long userId);
}
