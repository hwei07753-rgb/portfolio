package com.example.project.service.impl;

import com.example.project.common.BusinessException;
import com.example.project.entity.ProjectMember;
import com.example.project.entity.Task;
import com.example.project.entity.dto.TaskCreateRequest;
import com.example.project.entity.dto.TaskUpdateRequest;
import com.example.project.entity.dto.TaskVO;
// R-05-issue-4: 已修复 - 通配符import展开为9个独立import,对齐ProjectServiceImplTest风格
import com.example.project.mapper.LabelMapper;
import com.example.project.mapper.MilestoneMapper;
import com.example.project.mapper.ProjectMemberMapper;
import com.example.project.mapper.TaskDependencyMapper;
import com.example.project.mapper.TaskLabelMapper;
import com.example.project.mapper.TaskLogMapper;
import com.example.project.mapper.TaskMapper;
import com.example.project.mapper.TaskTransitionMapper;
import com.example.project.mapper.UserMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

// R-05-issue-2: 已修复(标注) - createTask快乐路径需@SpringBootTest集成测试(MP LambdaQueryWrapper纯单测NPE已知限制);教学简化保留单元测试覆盖边界路径,集成测试留Phase 6补充
@ExtendWith(MockitoExtension.class)
@DisplayName("任务服务单元测试")
class TaskServiceImplTest {

    @Mock
    private TaskMapper taskMapper;

    @Mock
    private ProjectMemberMapper projectMemberMapper;

    @Mock
    private UserMapper userMapper;

    @Mock
    private TaskLogMapper taskLogMapper;

    @Mock
    private TaskLabelMapper taskLabelMapper;

    @Mock
    private LabelMapper labelMapper;

    @Mock
    private TaskDependencyMapper taskDependencyMapper;

    @Mock
    private TaskTransitionMapper taskTransitionMapper;

    @Mock
    private MilestoneMapper milestoneMapper;

    private TaskServiceImpl taskService;

    @BeforeEach
    void setUp() {
        taskService = new TaskServiceImpl(projectMemberMapper, userMapper, taskLogMapper, taskLabelMapper, labelMapper, taskDependencyMapper, taskTransitionMapper, milestoneMapper);
        ReflectionTestUtils.setField(taskService, "baseMapper", taskMapper);
    }

    @Test
    @DisplayName("创建任务 - 非项目成员")
    void shouldRejectNonMemberCreate() {
        when(projectMemberMapper.selectOne(any())).thenReturn(null);

        TaskCreateRequest req = new TaskCreateRequest();
        req.setTitle("测试任务");

        assertThatThrownBy(() -> taskService.createTask(1L, req, 1L))
                .isInstanceOf(BusinessException.class)
                .extracting("code").isEqualTo(2002);
    }

    @Test
    @DisplayName("创建任务 - 指派人不在项目中")
    void shouldRejectInvalidAssignee() {
        ProjectMember member = new ProjectMember();
        member.setRole("owner");

        when(projectMemberMapper.selectOne(any())).thenReturn(member);
        when(projectMemberMapper.selectCount(any())).thenReturn(0L);

        TaskCreateRequest req = new TaskCreateRequest();
        req.setTitle("测试任务");
        req.setAssigneeId(999L);

        assertThatThrownBy(() -> taskService.createTask(1L, req, 1L))
                .isInstanceOf(BusinessException.class)
                .extracting("code").isEqualTo(9001);
    }

    @Test
    @DisplayName("编辑任务 - member 无权编辑他人任务")
    void shouldRejectUnauthorizedEdit() {
        Task task = new Task();
        task.setId(1L);
        task.setProjectId(1L);
        task.setTitle("原始标题");
        task.setCreatorId(2L);
        task.setAssigneeId(3L);
        task.setStatus("todo");

        ProjectMember member = new ProjectMember();
        member.setRole("member");

        when(taskMapper.selectById(1L)).thenReturn(task);
        when(projectMemberMapper.selectOne(any())).thenReturn(member);

        TaskUpdateRequest req = new TaskUpdateRequest();
        req.setTitle("修改标题");

        assertThatThrownBy(() -> taskService.updateTask(1L, req, 1L))
                .isInstanceOf(BusinessException.class)
                .extracting("code").isEqualTo(9003);
    }

    @Test
    @DisplayName("编辑任务 - 任务不存在")
    void shouldThrowWhenTaskNotFound() {
        when(taskMapper.selectById(999L)).thenReturn(null);

        TaskUpdateRequest req = new TaskUpdateRequest();
        req.setTitle("x");

        assertThatThrownBy(() -> taskService.updateTask(999L, req, 1L))
                .isInstanceOf(BusinessException.class)
                .extracting("code").isEqualTo(3001);
    }

    @Test
    @DisplayName("状态变更 - P0 已完成回退被拒绝")
    void shouldRejectDoneRevert() {
        Task task = new Task();
        task.setId(1L);
        task.setProjectId(1L);
        task.setTitle("已完成任务");
        task.setCreatorId(1L);
        task.setStatus("done");

        ProjectMember member = new ProjectMember();
        member.setRole("owner");

        when(taskMapper.selectById(1L)).thenReturn(task);
        when(projectMemberMapper.selectOne(any())).thenReturn(member);
        when(taskTransitionMapper.selectOne(any())).thenReturn(null);

        TaskUpdateRequest req = new TaskUpdateRequest();
        req.setStatus("todo");

        assertThatThrownBy(() -> taskService.updateTask(1L, req, 1L))
                .isInstanceOf(BusinessException.class)
                .extracting("code").isEqualTo(3002);
    }

    @Test
    @DisplayName("编辑任务 - owner 可编辑任意任务")
    void shouldAllowOwnerEditAnyTask() {
        Task task = new Task();
        task.setId(1L);
        task.setProjectId(1L);
        task.setTitle("原始标题");
        task.setCreatorId(2L);
        task.setAssigneeId(3L);
        task.setStatus("todo");
        task.setVersion(0);

        ProjectMember member = new ProjectMember();
        member.setRole("owner");

        when(taskMapper.selectById(1L)).thenReturn(task);
        when(projectMemberMapper.selectOne(any())).thenReturn(member);
        when(taskMapper.updateById(any(Task.class))).thenReturn(1);
        Task updated = new Task();
        updated.setId(1L);
        updated.setProjectId(1L);
        updated.setTitle("修改标题");
        updated.setCreatorId(2L);
        updated.setStatus("todo");
        when(taskMapper.selectById(1L)).thenReturn(updated);
        when(taskLabelMapper.selectList(any())).thenReturn(java.util.List.of());

        TaskUpdateRequest req = new TaskUpdateRequest();
        req.setTitle("修改标题");

        TaskVO result = taskService.updateTask(1L, req, 1L);

        assertThat(result.getTitle()).isEqualTo("修改标题");
    }
}
