package com.example.project.service.impl;

import com.example.project.common.BusinessException;
import com.example.project.entity.Project;
import com.example.project.entity.ProjectMember;
import com.example.project.entity.User;
import com.example.project.entity.dto.MemberReplaceRequest;
import com.example.project.entity.dto.ProjectCreateRequest;
import com.example.project.entity.dto.ProjectUpdateRequest;
import com.example.project.entity.dto.ProjectVO;
import com.example.project.mapper.ProjectMapper;
import com.example.project.mapper.ProjectMemberMapper;
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

// R-05-issue-6: 已修复 - 补充归档幂等测试 shouldArchiveProjectIdempotently
@ExtendWith(MockitoExtension.class)
@DisplayName("项目服务单元测试")
class ProjectServiceImplTest {

    @Mock
    private ProjectMapper projectMapper;

    @Mock
    private ProjectMemberMapper projectMemberMapper;

    @Mock
    private UserMapper userMapper;

    private ProjectServiceImpl projectService;

    @BeforeEach
    void setUp() {
        projectService = new ProjectServiceImpl(projectMemberMapper, userMapper);
        ReflectionTestUtils.setField(projectService, "baseMapper", projectMapper);
    }

    @Test
    @DisplayName("创建项目 - 自动添加创建者为 owner")
    void shouldCreateProjectWithOwner() {
        ProjectCreateRequest req = new ProjectCreateRequest();
        req.setName("新项目");

        when(projectMapper.insert(any(Project.class))).thenAnswer(inv -> {
            Project p = inv.getArgument(0);
            p.setId(1L);
            return 1;
        });
        when(projectMemberMapper.insert(any(ProjectMember.class))).thenReturn(1);
        // R-05-issue-5: 已修复 - owner user stub返回完整User+补充ownerName断言
        User owner = new User();
        owner.setId(1L);
        owner.setUsername("admin");
        when(userMapper.selectById(1L)).thenReturn(owner);
        when(projectMemberMapper.selectCount(any())).thenReturn(1L);
        when(projectMapper.countTasksByProjectId(1L)).thenReturn(0);

        ProjectVO result = projectService.createProject(1L, req);

        assertThat(result.getName()).isEqualTo("新项目");
        assertThat(result.getMyRole()).isEqualTo("owner");
        assertThat(result.getOwnerName()).isEqualTo("admin");
    }

    @Test
    @DisplayName("获取项目详情 - 正常")
    void shouldGetProject() {
        Project project = new Project();
        project.setId(1L);
        project.setName("测试项目");
        project.setOwnerId(1L);
        project.setArchived(0);

        ProjectMember member = new ProjectMember();
        member.setRole("owner");

        User owner = new User();
        owner.setId(1L);
        owner.setUsername("admin");

        when(projectMapper.selectById(1L)).thenReturn(project);
        when(projectMemberMapper.selectOne(any())).thenReturn(member);
        when(userMapper.selectById(1L)).thenReturn(owner);
        when(projectMemberMapper.selectCount(any())).thenReturn(1L);
        when(projectMapper.countTasksByProjectId(1L)).thenReturn(3);

        ProjectVO result = projectService.getProject(1L, 1L);

        assertThat(result.getName()).isEqualTo("测试项目");
        assertThat(result.getOwnerName()).isEqualTo("admin");
        assertThat(result.getMyRole()).isEqualTo("owner");
        assertThat(result.getTaskCount()).isEqualTo(3);
    }

    @Test
    @DisplayName("获取项目详情 - 项目不存在")
    void shouldThrowWhenProjectNotFound() {
        when(projectMapper.selectById(999L)).thenReturn(null);

        assertThatThrownBy(() -> projectService.getProject(999L, 1L))
                .isInstanceOf(BusinessException.class)
                .extracting("code").isEqualTo(2001);
    }

    @Test
    @DisplayName("获取项目详情 - 非项目成员")
    void shouldThrowWhenNotMember() {
        Project project = new Project();
        project.setId(1L);
        project.setName("测试项目");
        project.setOwnerId(2L);

        when(projectMapper.selectById(1L)).thenReturn(project);
        when(projectMemberMapper.selectOne(any())).thenReturn(null);

        assertThatThrownBy(() -> projectService.getProject(1L, 1L))
                .isInstanceOf(BusinessException.class)
                .extracting("code").isEqualTo(2002);
    }

    @Test
    @DisplayName("修改项目 - 非 owner 不可操作")
    void shouldRejectNonOwnerUpdate() {
        Project project = new Project();
        project.setId(1L);
        project.setName("测试项目");

        ProjectMember member = new ProjectMember();
        member.setRole("member");

        when(projectMapper.selectById(1L)).thenReturn(project);
        when(projectMemberMapper.selectOne(any())).thenReturn(member);

        ProjectUpdateRequest req = new ProjectUpdateRequest();
        req.setName("新名称");

        assertThatThrownBy(() -> projectService.updateProject(1L, req, 1L))
                .isInstanceOf(BusinessException.class)
                .extracting("code").isEqualTo(2003);
    }

    @Test
    @DisplayName("整表替换成员 - 至少保留一名 owner")
    void shouldRejectWhenNoOwner() {
        Project project = new Project();
        project.setId(1L);
        project.setName("测试项目");

        ProjectMember selfMembership = new ProjectMember();
        selfMembership.setRole("owner");

        when(projectMapper.selectById(1L)).thenReturn(project);
        when(projectMemberMapper.selectOne(any())).thenReturn(selfMembership);

        MemberReplaceRequest.MemberItem item = new MemberReplaceRequest.MemberItem();
        item.setUserId(2L);
        item.setRole("member");
        List<MemberReplaceRequest.MemberItem> members = List.of(item);

        assertThatThrownBy(() -> projectService.replaceMembers(1L, 1L, members))
                .isInstanceOf(BusinessException.class)
                .extracting("code").isEqualTo(4002);
    }

    @Test
    @DisplayName("归档项目 - 幂等重复归档（条件UPDATE WHERE archived=0 静默）")
    void shouldArchiveProjectIdempotently() {
        Project project = new Project();
        project.setId(1L);
        project.setName("测试项目");
        project.setOwnerId(1L);
        project.setArchived(0);

        ProjectMember member = new ProjectMember();
        member.setRole("owner");

        when(projectMapper.selectById(1L)).thenReturn(project);
        when(projectMemberMapper.selectOne(any())).thenReturn(member);
        // 模拟条件UPDATE:WHERE archived=0,当前archived=0→updateById返回1→成功
        when(projectMapper.updateById(any(Project.class))).thenReturn(1);
        when(projectMemberMapper.selectCount(any())).thenReturn(1L);
        when(projectMapper.countTasksByProjectId(1L)).thenReturn(0);
        when(userMapper.selectById(1L)).thenReturn(null);

        ProjectUpdateRequest req = new ProjectUpdateRequest();
        req.setArchived(true);

        ProjectVO result = projectService.updateProject(1L, req, 1L);
        assertThat(result).isNotNull();
    }
}
