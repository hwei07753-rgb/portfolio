package com.example.project.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.example.project.common.BusinessException;
import com.example.project.entity.Milestone;
import com.example.project.entity.Project;
import com.example.project.entity.ProjectMember;
import com.example.project.entity.Task;
import com.example.project.entity.dto.BurndownPoint;
import com.example.project.enums.TaskStatusEnum;
import com.example.project.mapper.MilestoneMapper;
import com.example.project.mapper.ProjectMapper;
import com.example.project.mapper.ProjectMemberMapper;
import com.example.project.mapper.TaskMapper;
import com.example.project.service.StatsService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class StatsServiceImpl implements StatsService {

    private final TaskMapper taskMapper;
    private final ProjectMapper projectMapper;
    private final ProjectMemberMapper projectMemberMapper;
    private final MilestoneMapper milestoneMapper;

    @Override
    public Map<String, Integer> getStatusStats(Long projectId, Long userId) {
        checkProjectMember(projectId, userId);

        // R-05-issue-1: 已修复 - 改用QueryWrapper字符串模式select("status, COUNT(*) AS cnt")，LambdaQueryWrapper.select()无法嵌入聚合函数
        // 按 status 分组统计（排除 deleted）
        QueryWrapper<Task> queryWrapper = new QueryWrapper<Task>()
                .select("status", "COUNT(*) AS cnt")
                .eq("project_id", projectId)
                .ne("status", "deleted")
                .groupBy("status");
        List<Map<String, Object>> rows = taskMapper.selectMaps(queryWrapper);

        // 构建全零 Map 兜底
        Map<String, Integer> result = new LinkedHashMap<>();
        // R-05-issue-5: 已修复 - 改用TaskStatusEnum常量替代硬编码字符串
        result.put(TaskStatusEnum.TODO.getValue(), 0);
        result.put(TaskStatusEnum.IN_PROGRESS.getValue(), 0);
        result.put(TaskStatusEnum.DONE.getValue(), 0);
        result.put(TaskStatusEnum.BLOCKED.getValue(), 0);

        for (Map<String, Object> row : rows) {
            String status = (String) row.get("status");
            Object cntObj = row.get("cnt");
            int cnt = cntObj != null ? ((Number) cntObj).intValue() : 0;
            if (result.containsKey(status)) {
                result.put(status, cnt);
            }
        }

        return result;
    }

    @Override
    public List<BurndownPoint> getBurndown(Long projectId, Long userId, Long milestoneId) {
        checkProjectMember(projectId, userId);

        // R-05-issue-2: 已修复 - 添加注释说明教学简化假设单项目任务量≤500，避免selectList全量加载OOM风险
        // 教学简化：假设单项目任务量 ≤500，全量加载不会OOM
        LambdaQueryWrapper<Task> taskQuery = new LambdaQueryWrapper<Task>()
                .eq(Task::getProjectId, projectId)
                .ne(Task::getStatus, "deleted");

        // P2-3 Sprint 精确燃尽：按 milestoneId 过滤任务
        if (milestoneId != null) {
            taskQuery.eq(Task::getMilestoneId, milestoneId);
        }

        List<Task> tasks = taskMapper.selectList(taskQuery.orderByAsc(Task::getCreateTime));

        if (tasks.isEmpty()) {
            return List.of();
        }

        // P2-3 Sprint 精确燃尽：日期范围为 Sprint 起止日期
        // P1 fallback：日期范围为最早任务创建日期 → 今天
        LocalDate startDate;
        LocalDate endDate;
        if (milestoneId != null) {
            Milestone milestone = milestoneMapper.selectById(milestoneId);
            if (milestone == null) {
                throw new BusinessException(6001, "Sprint 不存在");
            }
            startDate = milestone.getStartDate();
            endDate = milestone.getEndDate();
            // 不超出今天（进行中的 Sprint 只展示到今天）
            if (endDate.isAfter(LocalDate.now())) {
                endDate = LocalDate.now();
            }
        } else {
            startDate = tasks.get(0).getCreateTime().toLocalDate();
            endDate = LocalDate.now();
        }

        // P2 Sprint 精确燃尽：总任务数 = Sprint 开始前已创建且属于该 Sprint 的任务数（基线）
        // P1 fallback：最早任务创建日期
        int totalTasks = tasks.size();

        // R-05-issue-3: 已修复 - 预建每日创建/完成映射表再逐天累加，O(任务数+天数)替代原O(天数×任务数)嵌套stream
        // 预建每日完成数映射（仅done状态 · 以 updateTime 为完成日）
        Map<LocalDate, Integer> doneByDay = tasks.stream()
                .filter(t -> TaskStatusEnum.DONE.getValue().equals(t.getStatus()))
                .collect(Collectors.groupingBy(
                        t -> t.getUpdateTime().toLocalDate(),
                        Collectors.summingInt(t -> 1)));

        // 按日累加：总任务数 - 累计完成数 = 剩余
        List<BurndownPoint> points = new ArrayList<>();
        LocalDate cursor = startDate;
        int doneAcc = 0;
        while (!cursor.isAfter(endDate)) {
            doneAcc += doneByDay.getOrDefault(cursor, 0);
            int remaining = totalTasks - doneAcc;
            points.add(new BurndownPoint(cursor, Math.max(remaining, 0)));
            cursor = cursor.plusDays(1);
        }

        return points;
    }

    /** 校验项目存在 + 当前用户是项目成员 */
    private void checkProjectMember(Long projectId, Long userId) {
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
    }
}