package com.example.project.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.example.project.common.BusinessException;
import com.example.project.entity.ProjectMember;
import com.example.project.entity.Task;
import com.example.project.entity.TaskDependency;
import com.example.project.entity.dto.DependencyCreateRequest;
import com.example.project.entity.dto.TaskDependencyVO;
import com.example.project.mapper.ProjectMemberMapper;
import com.example.project.mapper.TaskDependencyMapper;
import com.example.project.mapper.TaskMapper;
import com.example.project.service.TaskDependencyService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayDeque;
import java.util.Deque;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

@Slf4j
@Service
@RequiredArgsConstructor
public class TaskDependencyServiceImpl extends ServiceImpl<TaskDependencyMapper, TaskDependency> implements TaskDependencyService {

    private final TaskMapper taskMapper;
    private final ProjectMemberMapper projectMemberMapper;

    @Override
    @Transactional
    public TaskDependencyVO createDependency(Long projectId, DependencyCreateRequest request, Long userId) {
        // 校验项目成员
        checkProjectMember(projectId, userId);

        Long predecessorId = request.getPredecessorTaskId();
        Long successorId = request.getSuccessorTaskId();

        if (predecessorId.equals(successorId)) {
            throw new BusinessException(9001, "前置任务和后置任务不能相同");
        }

        // 校验两个任务都存在且属于该项目
        Task predecessor = taskMapper.selectById(predecessorId);
        if (predecessor == null || !predecessor.getProjectId().equals(projectId)) {
            throw new BusinessException(3001, "前置任务不存在");
        }
        Task successor = taskMapper.selectById(successorId);
        if (successor == null || !successor.getProjectId().equals(projectId)) {
            throw new BusinessException(3001, "后置任务不存在");
        }

        // R-05-issue-2: 已修复 - 移除selectCount检查,insert用try-catch DuplicateKeyException抛BusinessException(7001),并发安全
        // 循环依赖检测：如果把 A→B 加入后，从 B 出发沿后继边能否走到 A
        if (wouldCreateCycle(projectId, predecessorId, successorId)) {
            throw new BusinessException(7002, "检测到循环依赖，无法保存");
        }

        String depType = request.getDependencyType() != null ? request.getDependencyType() : "FS";
        if (!"FS".equals(depType)) {
            throw new BusinessException(9001, "仅支持 FS（完成-开始）依赖类型");
        }

        TaskDependency dep = new TaskDependency();
        dep.setProjectId(projectId);
        dep.setPredecessorTaskId(predecessorId);
        dep.setSuccessorTaskId(successorId);
        dep.setDependencyType(depType);
        try {
            baseMapper.insert(dep);
        } catch (DuplicateKeyException e) {
            throw new BusinessException(7001, "依赖已存在");
        }

        log.info("依赖创建成功: {} → {} (FS), projectId={}, userId={}", predecessorId, successorId, projectId, userId);

        TaskDependencyVO vo = new TaskDependencyVO();
        vo.setId(dep.getId());
        vo.setProjectId(dep.getProjectId());
        vo.setPredecessorTaskId(dep.getPredecessorTaskId());
        vo.setSuccessorTaskId(dep.getSuccessorTaskId());
        vo.setDependencyType(dep.getDependencyType());
        vo.setCreateTime(dep.getCreateTime());
        return vo;
    }

    @Override
    @Transactional
    public void deleteDependency(Long projectId, Long dependencyId, Long userId) {
        checkProjectMember(projectId, userId);

        TaskDependency dep = baseMapper.selectById(dependencyId);
        if (dep == null || !dep.getProjectId().equals(projectId)) {
            throw new BusinessException(7003, "依赖不存在");
        }

        baseMapper.deleteById(dependencyId);
        log.info("依赖已删除: id={}, {} → {}, userId={}", dependencyId, dep.getPredecessorTaskId(), dep.getSuccessorTaskId(), userId);
    }

    /** BFS 检测新增 A→B 是否形成环：从 B 出发沿后继边遍历，看是否可达 A */
    private boolean wouldCreateCycle(Long projectId, Long predecessorId, Long successorId) {
        // 收集项目中所有依赖边
        List<TaskDependency> allDeps = baseMapper.selectList(
                new LambdaQueryWrapper<TaskDependency>().eq(TaskDependency::getProjectId, projectId));

        // 构建邻接表（predecessor → [successor]）
        Map<Long, Set<Long>> graph = new HashMap<>();
        for (TaskDependency d : allDeps) {
            graph.computeIfAbsent(d.getPredecessorTaskId(), k -> new HashSet<>()).add(d.getSuccessorTaskId());
        }
        // 加入待检测的新边
        graph.computeIfAbsent(predecessorId, k -> new HashSet<>()).add(successorId);

        // BFS 从 successorId 出发，看能否到达 predecessorId
        Set<Long> visited = new HashSet<>();
        Deque<Long> queue = new ArrayDeque<>();
        queue.add(successorId);
        while (!queue.isEmpty()) {
            Long current = queue.poll();
            if (current.equals(predecessorId)) return true;
            if (!visited.add(current)) continue;
            Set<Long> neighbors = graph.get(current);
            if (neighbors != null) {
                for (Long next : neighbors) {
                    if (!visited.contains(next)) queue.add(next);
                }
            }
        }
        return false;
    }

    private void checkProjectMember(Long projectId, Long userId) {
        ProjectMember membership = projectMemberMapper.selectOne(
                new LambdaQueryWrapper<ProjectMember>()
                        .eq(ProjectMember::getProjectId, projectId)
                        .eq(ProjectMember::getUserId, userId));
        if (membership == null) {
            throw new BusinessException(2002, "非项目成员");
        }
    }
}
