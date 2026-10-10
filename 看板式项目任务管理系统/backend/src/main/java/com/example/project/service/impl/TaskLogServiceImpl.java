package com.example.project.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.example.project.common.BusinessException;
import com.example.project.entity.ProjectMember;
import com.example.project.entity.Task;
import com.example.project.entity.TaskLog;
import com.example.project.entity.User;
import com.example.project.entity.dto.TaskLogVO;
import com.example.project.mapper.ProjectMemberMapper;
import com.example.project.mapper.TaskLogMapper;
import com.example.project.mapper.TaskMapper;
import com.example.project.mapper.UserMapper;
import com.example.project.service.TaskLogService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
// R-05-issue-2: 已修复 - 继承 ServiceImpl<TaskLogMapper, TaskLog>,与项目其他 ServiceImpl 统一风格
public class TaskLogServiceImpl extends ServiceImpl<TaskLogMapper, TaskLog> implements TaskLogService {

    private final TaskLogMapper taskLogMapper;
    private final TaskMapper taskMapper;
    private final ProjectMemberMapper projectMemberMapper;
    private final UserMapper userMapper;

    @Override
    public List<TaskLogVO> listLogs(Long taskId, Long userId) {
        Task task = taskMapper.selectById(taskId);
        if (task == null) {
            throw new BusinessException(3001, "任务不存在");
        }

        checkProjectMember(task.getProjectId(), userId);

        List<TaskLog> logs = taskLogMapper.selectList(
                new LambdaQueryWrapper<TaskLog>()
                        .eq(TaskLog::getTaskId, taskId)
                        .orderByDesc(TaskLog::getCreateTime)
        );

        Set<Long> userIds = logs.stream().map(TaskLog::getUserId).collect(Collectors.toSet());
        Map<Long, User> userMap = userIds.isEmpty() ? Map.of()
                : userMapper.selectBatchIds(userIds).stream()
                        .collect(Collectors.toMap(User::getId, u -> u));

        return logs.stream().map(log -> toVO(log, userMap)).toList();
    }

    @Override
    @Transactional
    public TaskLogVO createComment(Long taskId, String content, Long userId) {
        Task task = taskMapper.selectById(taskId);
        if (task == null) {
            throw new BusinessException(3001, "任务不存在");
        }

        if ("deleted".equals(task.getStatus())) {
            throw new BusinessException(3101, "任务已删除，无法评论");
        }

        checkProjectMember(task.getProjectId(), userId);

        // D-01-fix-2026-05-18: 局部变量 log 遮蔽 @Slf4j logger → 重命名为 commentLog
        TaskLog commentLog = new TaskLog();
        commentLog.setTaskId(taskId);
        commentLog.setUserId(userId);
        commentLog.setType("comment");
        commentLog.setContent(content);

        taskLogMapper.insert(commentLog);

        User user = userMapper.selectById(userId);

        TaskLogVO vo = new TaskLogVO();
        vo.setId(commentLog.getId());
        vo.setTaskId(commentLog.getTaskId());
        vo.setUserId(commentLog.getUserId());
        vo.setUsername(user != null ? user.getUsername() : null);
        vo.setType(commentLog.getType());
        vo.setAction(commentLog.getAction());
        vo.setContent(commentLog.getContent());
        vo.setCreateTime(commentLog.getCreateTime());

        log.info("评论发送成功: taskId={}, userId={}", taskId, userId);
        return vo;
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

    private TaskLogVO toVO(TaskLog log, Map<Long, User> userMap) {
        TaskLogVO vo = new TaskLogVO();
        vo.setId(log.getId());
        vo.setTaskId(log.getTaskId());
        vo.setUserId(log.getUserId());
        User user = userMap.get(log.getUserId());
        vo.setUsername(user != null ? user.getUsername() : null);
        vo.setType(log.getType());
        vo.setAction(log.getAction());
        vo.setContent(log.getContent());
        vo.setCreateTime(log.getCreateTime());
        return vo;
    }
}