package com.example.project.service.impl;

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
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
@DisplayName("任务活动流服务单元测试")
class TaskLogServiceImplTest {

    @Mock
    private TaskLogMapper taskLogMapper;

    @Mock
    private TaskMapper taskMapper;

    @Mock
    private ProjectMemberMapper projectMemberMapper;

    @Mock
    private UserMapper userMapper;

    private TaskLogServiceImpl taskLogService;

    @BeforeEach
    void setUp() {
        taskLogService = new TaskLogServiceImpl(taskLogMapper, taskMapper, projectMemberMapper, userMapper);
        ReflectionTestUtils.setField(taskLogService, "baseMapper", taskLogMapper);
    }

    @Test
    @DisplayName("查看活动流 - 正常流程")
    void shouldListLogs() {
        Task task = new Task();
        task.setId(1L);
        task.setProjectId(1L);

        ProjectMember member = new ProjectMember();
        member.setRole("owner");

        User user = new User();
        user.setId(1L);
        user.setUsername("admin");

        TaskLog log = new TaskLog();
        log.setId(1L);
        log.setTaskId(1L);
        log.setUserId(1L);
        log.setType("system");
        log.setAction("created");

        when(taskMapper.selectById(1L)).thenReturn(task);
        when(projectMemberMapper.selectOne(any())).thenReturn(member);
        when(taskLogMapper.selectList(any())).thenReturn(List.of(log));
        when(userMapper.selectBatchIds(any())).thenReturn(List.of(user));

        List<TaskLogVO> result = taskLogService.listLogs(1L, 1L);

        assertThat(result).hasSize(1);
        assertThat(result.get(0).getUsername()).isEqualTo("admin");
        assertThat(result.get(0).getAction()).isEqualTo("created");
    }

    @Test
    @DisplayName("查看活动流 - 任务不存在")
    void shouldThrowWhenTaskNotFoundForLogs() {
        when(taskMapper.selectById(999L)).thenReturn(null);

        assertThatThrownBy(() -> taskLogService.listLogs(999L, 1L))
                .isInstanceOf(BusinessException.class)
                .extracting("code").isEqualTo(3001);
    }

    @Test
    @DisplayName("查看活动流 - 非项目成员")
    void shouldRejectNonMemberForLogs() {
        Task task = new Task();
        task.setId(1L);
        task.setProjectId(1L);

        when(taskMapper.selectById(1L)).thenReturn(task);
        when(projectMemberMapper.selectOne(any())).thenReturn(null);

        assertThatThrownBy(() -> taskLogService.listLogs(1L, 999L))
                .isInstanceOf(BusinessException.class)
                .extracting("code").isEqualTo(2002);
    }

    @Test
    @DisplayName("添加评论 - 正常流程")
    void shouldCreateComment() {
        Task task = new Task();
        task.setId(1L);
        task.setProjectId(1L);
        task.setStatus("todo");

        ProjectMember member = new ProjectMember();
        member.setRole("member");

        User user = new User();
        user.setId(1L);
        user.setUsername("admin");

        when(taskMapper.selectById(1L)).thenReturn(task);
        when(projectMemberMapper.selectOne(any())).thenReturn(member);
        when(taskLogMapper.insert(any(TaskLog.class))).thenReturn(1);
        when(userMapper.selectById(1L)).thenReturn(user);

        TaskLogVO result = taskLogService.createComment(1L, "评论内容", 1L);

        assertThat(result.getContent()).isEqualTo("评论内容");
        assertThat(result.getType()).isEqualTo("comment");
        assertThat(result.getUsername()).isEqualTo("admin");
    }

    @Test
    @DisplayName("添加评论 - 已删除任务不可评论")
    void shouldRejectCommentOnDeletedTask() {
        Task task = new Task();
        task.setId(1L);
        task.setProjectId(1L);
        task.setStatus("deleted");

        when(taskMapper.selectById(1L)).thenReturn(task);

        assertThatThrownBy(() -> taskLogService.createComment(1L, "评论", 1L))
                .isInstanceOf(BusinessException.class)
                .extracting("code").isEqualTo(3101);
    }
}
