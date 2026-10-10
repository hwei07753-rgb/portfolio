package com.example.project.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.example.project.common.BusinessException;
import com.example.project.entity.Project;
import com.example.project.entity.ProjectMember;
import com.example.project.entity.User;
import com.example.project.entity.dto.MemberReplaceRequest;
import com.example.project.entity.dto.MemberVO;
import com.example.project.entity.dto.ProjectCreateRequest;
import com.example.project.entity.dto.ProjectUpdateRequest;
import com.example.project.entity.dto.ProjectVO;
import com.example.project.mapper.ProjectMapper;
import com.example.project.mapper.ProjectMemberMapper;
import com.example.project.mapper.UserMapper;
import com.example.project.service.ProjectService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class ProjectServiceImpl extends ServiceImpl<ProjectMapper, Project> implements ProjectService {

    private final ProjectMemberMapper projectMemberMapper;
    private final UserMapper userMapper;

    @Override
    public IPage<ProjectVO> listProjects(Long userId, Integer pageNum, Integer pageSize, Boolean includeArchived, String sortBy) {
        // 1. 查询用户参与的所有项目成员记录
        List<ProjectMember> memberships = projectMemberMapper.selectList(
                new LambdaQueryWrapper<ProjectMember>().eq(ProjectMember::getUserId, userId));
        if (memberships.isEmpty()) {
            return new Page<ProjectVO>(pageNum, pageSize, 0);
        }

        // 构建 projectId → myRole 映射
        Map<Long, String> roleMap = memberships.stream()
                .collect(Collectors.toMap(ProjectMember::getProjectId, ProjectMember::getRole, (a, b) -> a));
        List<Long> projectIds = memberships.stream().map(ProjectMember::getProjectId).toList();

        // 2. 分页查询项目
        LambdaQueryWrapper<Project> wrapper = new LambdaQueryWrapper<Project>()
                .in(Project::getId, projectIds);
        // sortBy白名单(controller层已校验) → 映射到排序字段
        // R-05-issue-2: 已修复 - sortBy参数通过白名单校验后映射到对应排序字段
        switch (sortBy) {
            case "create_time" -> wrapper.orderByDesc(Project::getCreateTime);
            case "update_time" -> wrapper.orderByDesc(Project::getUpdateTime);
            case "name" -> wrapper.orderByAsc(Project::getName);
            default -> wrapper.orderByDesc(Project::getId);
        }
        if (includeArchived == null || !includeArchived) {
            wrapper.eq(Project::getArchived, 0);
        }

        Page<Project> page = new Page<>(pageNum, pageSize);
        Page<Project> projectPage = baseMapper.selectPage(page, wrapper);

        // R-05-issue-1: 已修复 - 批量加载owner/memberCount/taskCount替代逐条N+1查询
        // 3. 批量加载统计数据
        List<Project> projects = projectPage.getRecords();

        // 3a. 批量查询owner用户
        List<Long> ownerIds = projects.stream().map(Project::getOwnerId).distinct().toList();
        Map<Long, User> ownerMap = ownerIds.isEmpty() ? Map.of()
                : userMapper.selectBatchIds(ownerIds).stream()
                        .collect(Collectors.toMap(User::getId, u -> u));

        // 3b. 批量查询memberCount（GROUP BY project_id + COUNT(*)）
        // D-01-fix-2026-05-21: LambdaQueryWrapper.select(ProjectMember::getProjectId) 只SELECT project_id无COUNT聚合,改用QueryWrapper显式select("project_id, COUNT(*) as cnt")
        Map<Long, Long> memberCountMap = projectIds.isEmpty() ? Map.of()
                : projectMemberMapper.selectMaps(
                        new QueryWrapper<ProjectMember>()
                                .select("project_id, COUNT(*) as cnt")
                                .in("project_id", projectIds)
                                .groupBy("project_id"))
                        .stream()
                        .collect(Collectors.toMap(
                                m -> (Long) m.get("project_id"),
                                m -> ((Number) m.getOrDefault("cnt", 0L)).longValue(),
                                (a, b) -> a));

        // 3c. 批量查询taskCount（GROUP BY project_id）
        Map<Long, Long> taskCountMap = projectIds.isEmpty() ? Map.of()
                : baseMapper.countTasksByProjectIds(projectIds).stream()
                        .collect(Collectors.toMap(
                                m -> (Long) m.get("project_id"),
                                m -> ((Number) m.get("cnt")).longValue(),
                                (a, b) -> a));

        // 4. 转换为 ProjectVO
        Page<ProjectVO> voPage = new Page<>(pageNum, pageSize, projectPage.getTotal());
        List<ProjectVO> voList = projects.stream().map(project -> {
            ProjectVO vo = new ProjectVO();
            vo.setId(project.getId());
            vo.setName(project.getName());
            vo.setOwnerId(project.getOwnerId());
            vo.setArchived(project.getArchived() != null && project.getArchived() == 1);
            vo.setMyRole(roleMap.get(project.getId()));
            vo.setCreateTime(project.getCreateTime());
            vo.setUpdateTime(project.getUpdateTime());

            User owner = ownerMap.get(project.getOwnerId());
            vo.setOwnerName(owner != null ? owner.getUsername() : null);

            vo.setMemberCount(memberCountMap.getOrDefault(project.getId(), 0L).intValue());
            vo.setTaskCount(taskCountMap.getOrDefault(project.getId(), 0L).intValue());

            return vo;
        }).toList();
        voPage.setRecords(voList);

        return voPage;
    }

    @Override
    @Transactional
    public ProjectVO createProject(Long userId, ProjectCreateRequest request) {
        // 1. 创建项目
        Project project = new Project();
        project.setName(request.getName());
        project.setOwnerId(userId);
        project.setArchived(0);
        baseMapper.insert(project);

        // 2. 自动添加创建者为 owner
        ProjectMember member = new ProjectMember();
        member.setProjectId(project.getId());
        member.setUserId(userId);
        member.setRole("owner");
        projectMemberMapper.insert(member);

        log.info("项目创建成功: name={}, ownerId={}", request.getName(), userId);

        // 3. 返回 ProjectVO
        return toVO(project, "owner");
    }

    @Override
    public ProjectVO getProject(Long projectId, Long userId) {
        Project project = baseMapper.selectById(projectId);
        if (project == null) {
            throw new BusinessException(2001, "项目不存在");
        }

        // 校验是否为项目成员
        ProjectMember membership = projectMemberMapper.selectOne(
                new LambdaQueryWrapper<ProjectMember>()
                        .eq(ProjectMember::getProjectId, projectId)
                        .eq(ProjectMember::getUserId, userId));
        if (membership == null) {
            throw new BusinessException(2002, "非项目成员");
        }

        return toVO(project, membership.getRole());
    }

    @Override
    @Transactional
    public ProjectVO updateProject(Long projectId, ProjectUpdateRequest request, Long userId) {
        Project project = baseMapper.selectById(projectId);
        if (project == null) {
            throw new BusinessException(2001, "项目不存在");
        }

        // 校验当前用户是否为该项目的 owner
        ProjectMember membership = projectMemberMapper.selectOne(
                new LambdaQueryWrapper<ProjectMember>()
                        .eq(ProjectMember::getProjectId, projectId)
                        .eq(ProjectMember::getUserId, userId));
        if (membership == null) {
            throw new BusinessException(2002, "非项目成员");
        }
        if (!"owner".equals(membership.getRole())) {
            throw new BusinessException(2003, "非项目 owner，无权操作");
        }

        boolean updated = false;

        // 修改项目名称
        if (request.getName() != null && !request.getName().isBlank()) {
            project.setName(request.getName());
            updated = true;
        }

        // 归档项目（幂等：条件UPDATE SET archived=1 WHERE id=? AND archived=0，对齐API_DESIGN §3.2约定）
        // R-05-issue-7: 已修复 - 归档改用数据库层条件UPDATE WHERE archived=0替代Java层检查，对齐API_DESIGN幂等约定
        boolean archived = false;
        if (request.getArchived() != null && request.getArchived()) {
            LambdaQueryWrapper<Project> archiveWrapper = new LambdaQueryWrapper<Project>()
                    .eq(Project::getId, projectId)
                    .eq(Project::getArchived, 0);
            Project archiveUpdate = new Project();
            archiveUpdate.setArchived(1);
            int rows = baseMapper.update(archiveUpdate, archiveWrapper);
            if (rows > 0) {
                archived = true;
                log.info("项目已归档: projectId={}, name={}", projectId, project.getName());
            }
        }

        // D-01-fix-2026-05-21: 同步 project.archived 防止 updateById 写回 0 撤销归档。改用两个 bool 分控：nameChanged→updateById，archived→已通过条件 UPDATE 完成
        if (updated) {
            if (archived) {
                project.setArchived(1);
            }
            baseMapper.updateById(project);
        }

        // 重新查询以获取最新数据
        project = baseMapper.selectById(projectId);
        return toVO(project, membership.getRole());
    }

    @Override
    public List<MemberVO> listMembers(Long projectId, Long userId) {
        // 1. 校验项目存在 + 当前用户是项目成员
        Project project = baseMapper.selectById(projectId);
        if (project == null) {
            throw new BusinessException(2001, "项目不存在");
        }
        ProjectMember selfMembership = projectMemberMapper.selectOne(
                new LambdaQueryWrapper<ProjectMember>()
                        .eq(ProjectMember::getProjectId, projectId)
                        .eq(ProjectMember::getUserId, userId));
        if (selfMembership == null) {
            throw new BusinessException(2002, "非项目成员");
        }
        if (!"owner".equals(selfMembership.getRole())) {
            throw new BusinessException(2003, "非项目 owner，无权查看成员");
        }

        // 2. 查询所有成员记录
        List<ProjectMember> members = projectMemberMapper.selectList(
                new LambdaQueryWrapper<ProjectMember>().eq(ProjectMember::getProjectId, projectId));

        // 3. 批量查询用户信息
        List<Long> userIds = members.stream().map(ProjectMember::getUserId).toList();
        // R-05-issue-9: 已修复 - 已删除用户(is_deleted=1)的MemberVO设username为"已注销用户"作为fallback，避免null值
        Map<Long, User> userMap = userIds.isEmpty() ? Map.of()
                : userMapper.selectBatchIds(userIds).stream()
                        .collect(Collectors.toMap(User::getId, u -> u));

        // 4. 组装 MemberVO
        return members.stream().map(m -> {
            MemberVO vo = new MemberVO();
            vo.setUserId(m.getUserId());
            vo.setRole(m.getRole());
            User u = userMap.get(m.getUserId());
            if (u != null) {
                vo.setUsername(u.getUsername());
                vo.setNickname(u.getNickname());
            } else {
                vo.setUsername("已注销用户");
                vo.setNickname(null);
            }
            return vo;
        }).toList();
    }

    @Override
    @Transactional
    public void replaceMembers(Long projectId, Long userId, List<MemberReplaceRequest.MemberItem> members) {
        // 1. 校验项目存在
        Project project = baseMapper.selectById(projectId);
        if (project == null) {
            throw new BusinessException(2001, "项目不存在");
        }

        // 2. 校验当前用户为 owner
        ProjectMember selfMembership = projectMemberMapper.selectOne(
                new LambdaQueryWrapper<ProjectMember>()
                        .eq(ProjectMember::getProjectId, projectId)
                        .eq(ProjectMember::getUserId, userId));
        if (selfMembership == null) {
            throw new BusinessException(2002, "非项目成员");
        }
        if (!"owner".equals(selfMembership.getRole())) {
            throw new BusinessException(4001, "非项目 owner，无权管理成员");
        }

        // 3. 校验至少保留一名 owner
        boolean hasOwner = members.stream().anyMatch(m -> "owner".equals(m.getRole()));
        if (!hasOwner) {
            throw new BusinessException(4002, "至少保留一名 owner");
        }

        // 4. 校验无重复 userId
        Set<Long> userIdSet = members.stream().map(MemberReplaceRequest.MemberItem::getUserId).collect(Collectors.toSet());
        if (userIdSet.size() != members.size()) {
            // R-05-issue-8: 已修复 - 改用4004业务码替代400(HTTP语义冲突)，对齐API_DESIGN §3.3异常码表
            throw new BusinessException(4004, "成员列表中包含重复用户");
        }

        // 5. 校验所有 userId 在 user 表中存在
        List<Long> inputUserIds = new ArrayList<>(userIdSet);
        List<User> existingUsers = userMapper.selectBatchIds(inputUserIds);
        if (existingUsers.size() != inputUserIds.size()) {
            throw new BusinessException(4003, "用户不存在");
        }

        // 6. 事务内: DELETE 旧记录 + INSERT 新记录
        projectMemberMapper.delete(
                new LambdaQueryWrapper<ProjectMember>().eq(ProjectMember::getProjectId, projectId));

        List<ProjectMember> newMembers = members.stream().map(m -> {
            ProjectMember pm = new ProjectMember();
            pm.setProjectId(projectId);
            pm.setUserId(m.getUserId());
            pm.setRole(m.getRole());
            return pm;
        }).toList();

        for (ProjectMember pm : newMembers) {
            projectMemberMapper.insert(pm);
        }

        log.info("项目成员已更新: projectId={}, memberCount={}", projectId, newMembers.size());
    }

    /** 将 Project entity 转为 ProjectVO，补充统计字段 */
    private ProjectVO toVO(Project project, String myRole) {
        ProjectVO vo = new ProjectVO();
        vo.setId(project.getId());
        vo.setName(project.getName());
        vo.setOwnerId(project.getOwnerId());
        vo.setArchived(project.getArchived() != null && project.getArchived() == 1);
        vo.setMyRole(myRole);
        vo.setCreateTime(project.getCreateTime());
        // R-05-issue-1: 已修复 - toVO仅用于createProject/getProject/updateProject各单条记录,N+1不构成性能问题;listProjects已用批量加载优化
        vo.setUpdateTime(project.getUpdateTime());

        // ownerName
        User owner = userMapper.selectById(project.getOwnerId());
        vo.setOwnerName(owner != null ? owner.getUsername() : null);

        // memberCount
        Long memberCount = projectMemberMapper.selectCount(
                new LambdaQueryWrapper<ProjectMember>().eq(ProjectMember::getProjectId, project.getId()));
        vo.setMemberCount(memberCount.intValue());

        // taskCount
        int taskCount = baseMapper.countTasksByProjectId(project.getId());
        vo.setTaskCount(taskCount);

        return vo;
    }
}