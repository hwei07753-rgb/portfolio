package com.example.project.controller;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.example.project.common.Result;
import com.example.project.entity.dto.BurndownPoint;
import com.example.project.entity.dto.MemberReplaceRequest;
import com.example.project.entity.dto.MemberVO;
import com.example.project.entity.dto.PageResult;
import com.example.project.entity.dto.ProjectCreateRequest;
import com.example.project.entity.dto.ProjectUpdateRequest;
import com.example.project.entity.dto.ProjectVO;
import com.example.project.service.ProjectService;
import com.example.project.service.StatsService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestAttribute;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;
import java.util.Set;

@RestController
@RequestMapping("/api/projects")
@RequiredArgsConstructor
public class ProjectController {

    private final ProjectService projectService;
    private final StatsService statsService;

    /** 分页列表 */
    // R-05-issue-2: 已修复 - 添加sortBy参数，支持id/create_time/update_time/name白名单排序
    // R-05-issue-3: 已修复 - 添加@Min(1)/@Max(100)分页参数校验
    // R-05-issue-4: 已修复 - IPage转PageResult DTO，字段名对齐API_DESIGN(pageNum/pageSize替代current/size)
    // R-05-issue-6: 已修复 - @Validated从类级移至此方法,stats两个GET端点不再被无意义的校验覆盖
    @GetMapping
    @Validated
    public Result<PageResult<ProjectVO>> list(
            @RequestAttribute("userId") Long userId,
            @RequestParam(defaultValue = "1") @Min(1) Integer pageNum,
            @RequestParam(defaultValue = "10") @Max(100) Integer pageSize,
            @RequestParam(defaultValue = "false") Boolean includeArchived,
            @RequestParam(defaultValue = "id") String sortBy) {
        // sortBy白名单校验
        Set<String> allowedSortBy = Set.of("id", "create_time", "update_time", "name");
        String effectiveSortBy = allowedSortBy.contains(sortBy) ? sortBy : "id";
        IPage<ProjectVO> page = projectService.listProjects(userId, pageNum, pageSize, includeArchived, effectiveSortBy);
        PageResult<ProjectVO> result = PageResult.of(page.getRecords(), page.getTotal(), pageNum, pageSize);
        return Result.success(result);
    }

    /** 创建项目 */
    @PostMapping
    public Result<ProjectVO> create(
            @RequestAttribute("userId") Long userId,
            @RequestBody @Valid ProjectCreateRequest request) {
        ProjectVO vo = projectService.createProject(userId, request);
        return Result.success(vo, "项目创建成功");
    }

    /** 项目详情 */
    @GetMapping("/{id}")
    public Result<ProjectVO> detail(
            @PathVariable Long id,
            @RequestAttribute("userId") Long userId) {
        ProjectVO vo = projectService.getProject(id, userId);
        return Result.success(vo);
    }

    /** 修改项目名称 / 归档 */
    @PutMapping("/{id}")
    public Result<ProjectVO> update(
            @PathVariable Long id,
            @RequestBody @Valid ProjectUpdateRequest request,
            @RequestAttribute("userId") Long userId) {
        ProjectVO vo = projectService.updateProject(id, request, userId);
        return Result.success(vo, "项目更新成功");
    }

    /** 查看项目成员列表 */
    @GetMapping("/{id}/members")
    public Result<List<MemberVO>> listMembers(
            @PathVariable Long id,
            @RequestAttribute("userId") Long userId) {
        List<MemberVO> members = projectService.listMembers(id, userId);
        return Result.success(members);
    }

    /** 整表替换项目成员 */
    @PutMapping("/{id}/members")
    public Result<Void> replaceMembers(
            @PathVariable Long id,
            @RequestBody @Valid MemberReplaceRequest request,
            @RequestAttribute("userId") Long userId) {
        projectService.replaceMembers(id, userId, request.getMembers());
        return Result.success(null, "成员更新成功");
    }

    /** 按状态统计任务数量 */
    @GetMapping("/{id}/stats/status")
    public Result<Map<String, Integer>> statusStats(
            @PathVariable Long id,
            @RequestAttribute("userId") Long userId) {
        Map<String, Integer> stats = statsService.getStatusStats(id, userId);
        return Result.success(stats);
    }

    /** 燃尽图数据。可选 milestoneId 参数启用 Sprint 精确燃尽（P2） */
    @GetMapping("/{id}/stats/burndown")
    public Result<List<BurndownPoint>> burndown(
            @PathVariable Long id,
            @RequestAttribute("userId") Long userId,
            @RequestParam(required = false) Long milestoneId) {
        List<BurndownPoint> points = statsService.getBurndown(id, userId, milestoneId);
        return Result.success(points);
    }
}