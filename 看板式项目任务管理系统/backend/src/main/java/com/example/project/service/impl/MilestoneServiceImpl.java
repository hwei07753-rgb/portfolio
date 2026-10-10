package com.example.project.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.example.project.common.BusinessException;
import com.example.project.entity.Milestone;
import com.example.project.entity.Project;
import com.example.project.entity.ProjectMember;
import com.example.project.entity.Task;
import com.example.project.entity.dto.MilestoneCreateRequest;
import com.example.project.entity.dto.MilestoneVO;
import com.example.project.mapper.MilestoneMapper;
import com.example.project.mapper.ProjectMapper;
import com.example.project.mapper.ProjectMemberMapper;
import com.example.project.mapper.TaskMapper;
import com.example.project.service.MilestoneService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class MilestoneServiceImpl extends ServiceImpl<MilestoneMapper, Milestone> implements MilestoneService {

    private final ProjectMapper projectMapper;
    private final ProjectMemberMapper projectMemberMapper;
    private final TaskMapper taskMapper;

    @Override
    public List<MilestoneVO> listMilestones(Long projectId, Long userId) {
        checkProjectMember(projectId, userId);

        List<Milestone> milestones = baseMapper.selectList(
                new LambdaQueryWrapper<Milestone>()
                        .eq(Milestone::getProjectId, projectId)
                        .orderByAsc(Milestone::getStartDate));

        LocalDate today = LocalDate.now();

        // R-05-issue-2: 已修复 - 批量GROUP BY查询替代逐条selectCount，一次DB往返获取所有Sprint任务数
        java.util.Map<Long, Long> taskCountMap = new java.util.HashMap<>();
        if (!milestones.isEmpty()) {
            String milestoneIds = milestones.stream()
                    .map(m -> String.valueOf(m.getId()))
                    .reduce((a, b) -> a + "," + b).orElse("");
            taskMapper.countTasksByMilestoneIds(milestoneIds).forEach(row -> {
                Long mid = ((Number) row.get("milestoneId")).longValue();
                Long cnt = ((Number) row.get("taskCount")).longValue();
                taskCountMap.put(mid, cnt);
            });
        }

        return milestones.stream().map(m -> {
            MilestoneVO vo = new MilestoneVO();
            vo.setId(m.getId());
            vo.setName(m.getName());
            vo.setStartDate(m.getStartDate());
            vo.setEndDate(m.getEndDate());
            vo.setCreateTime(m.getCreateTime());

            // 状态由日期自动推断
            if (today.isBefore(m.getStartDate())) {
                vo.setStatus("upcoming");
            } else if (today.isAfter(m.getEndDate())) {
                vo.setStatus("completed");
            } else {
                vo.setStatus("active");
            }

            vo.setTaskCount(taskCountMap.getOrDefault(m.getId(), 0L).intValue());

            return vo;
        }).toList();
    }

    @Override
    @Transactional
    public MilestoneVO createMilestone(Long projectId, MilestoneCreateRequest request, Long userId) {
        // 校验项目成员 + owner 权限
        ProjectMember membership = checkProjectMember(projectId, userId);
        if (!"owner".equals(membership.getRole())) {
            throw new BusinessException(2003, "非项目 owner，无权操作");
        }

        // 校验起止日期
        if (request.getEndDate().isBefore(request.getStartDate())) {
            throw new BusinessException(9001, "结束日期不能早于开始日期");
        }

        Milestone milestone = new Milestone();
        milestone.setProjectId(projectId);
        milestone.setName(request.getName().trim());
        milestone.setStartDate(request.getStartDate());
        milestone.setEndDate(request.getEndDate());
        baseMapper.insert(milestone);

        log.info("Sprint创建成功: name={}, projectId={}, startDate={}, endDate={}",
                milestone.getName(), projectId, milestone.getStartDate(), milestone.getEndDate());

        // R-05-issue-3: 已修复 - insert后selectById重新加载，获取DB层DEFAULT CURRENT_TIMESTAMP填充的createTime等字段
        milestone = baseMapper.selectById(milestone.getId());

        MilestoneVO vo = new MilestoneVO();
        vo.setId(milestone.getId());
        vo.setName(milestone.getName());
        vo.setStartDate(milestone.getStartDate());
        vo.setEndDate(milestone.getEndDate());
        vo.setCreateTime(milestone.getCreateTime());
        // 新创建的 Sprint 状态按起止日期推断
        LocalDate today = LocalDate.now();
        if (today.isBefore(milestone.getStartDate())) {
            vo.setStatus("upcoming");
        } else if (today.isAfter(milestone.getEndDate())) {
            vo.setStatus("completed");
        } else {
            vo.setStatus("active");
        }
        vo.setTaskCount(0);

        return vo;
    }

    @Override
    @Transactional
    public void deleteMilestone(Long projectId, Long milestoneId, Long userId) {
        // 校验项目成员 + owner 权限
        ProjectMember membership = checkProjectMember(projectId, userId);
        if (!"owner".equals(membership.getRole())) {
            throw new BusinessException(2003, "非项目 owner，无权操作");
        }

        Milestone milestone = baseMapper.selectById(milestoneId);
        if (milestone == null || !milestone.getProjectId().equals(projectId)) {
            throw new BusinessException(6001, "Sprint 不存在");
        }

        // 删除 Sprint：外键 ON DELETE SET NULL 自动将关联任务的 milestone_id 设为 NULL
        baseMapper.deleteById(milestoneId);

        log.info("Sprint已删除: id={}, name={}, projectId={}", milestoneId, milestone.getName(), projectId);
    }

    /** 校验项目存在 + 当前用户是项目成员，返回成员记录 */
    private ProjectMember checkProjectMember(Long projectId, Long userId) {
        Project project = projectMapper.selectById(projectId);
        if (project == null) {
            throw new BusinessException(2001, "项目不存在");
        }
        ProjectMember membership = projectMemberMapper.selectOne(
                new LambdaQueryWrapper<ProjectMember>()
                        .eq(ProjectMember::getProjectId, projectId)
                        .eq(ProjectMember::getUserId, userId));
        if (membership == null) {
            throw new BusinessException(2002, "非项目成员");
        }
        return membership;
    }
}
