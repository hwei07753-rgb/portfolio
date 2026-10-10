package com.example.project.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.service.IService;
import com.example.project.entity.Project;
import com.example.project.entity.dto.MemberReplaceRequest;
import com.example.project.entity.dto.MemberVO;
import com.example.project.entity.dto.ProjectCreateRequest;
import com.example.project.entity.dto.ProjectUpdateRequest;
import com.example.project.entity.dto.ProjectVO;

import java.util.List;

public interface ProjectService extends IService<Project> {

    /** 分页查询当前用户参与的项目列表
     * @param userId 当前用户ID
     * @param pageNum 页码（从1开始）
     * @param pageSize 每页条数
     * @param includeArchived true=包含已归档项目, false/null=默认排除
     * @param sortBy 排序字段（id/create_time/update_time/name，已在controller层白名单校验） */
    // R-05-issue-6: 已修复 - 补充完整Javadoc（@param userId/pageNum/pageSize + sortBy）
    IPage<ProjectVO> listProjects(Long userId, Integer pageNum, Integer pageSize, Boolean includeArchived, String sortBy);

    /** 创建项目（自动添加当前用户为owner） */
    ProjectVO createProject(Long userId, ProjectCreateRequest request);

    /** 查看项目详情 */
    ProjectVO getProject(Long projectId, Long userId);

    /** 修改项目名称 / 归档项目 */
    ProjectVO updateProject(Long projectId, ProjectUpdateRequest request, Long userId);

    /** 查看项目成员列表 */
    List<MemberVO> listMembers(Long projectId, Long userId);

    /** 整表替换项目成员（事务内 DELETE + INSERT） */
    void replaceMembers(Long projectId, Long userId, List<MemberReplaceRequest.MemberItem> members);
}