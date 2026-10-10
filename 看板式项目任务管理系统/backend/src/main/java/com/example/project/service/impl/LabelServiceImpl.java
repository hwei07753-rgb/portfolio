package com.example.project.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.example.project.common.BusinessException;
import com.example.project.entity.Label;
import com.example.project.entity.Project;
import com.example.project.entity.ProjectMember;
import com.example.project.entity.TaskLabel;
import com.example.project.entity.dto.LabelCreateRequest;
import com.example.project.entity.dto.LabelVO;
import com.example.project.mapper.LabelMapper;
import com.example.project.mapper.ProjectMapper;
import com.example.project.mapper.ProjectMemberMapper;
import com.example.project.mapper.TaskLabelMapper;
import com.example.project.service.LabelService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class LabelServiceImpl extends ServiceImpl<LabelMapper, Label> implements LabelService {

    private final ProjectMapper projectMapper;
    private final ProjectMemberMapper projectMemberMapper;
    private final TaskLabelMapper taskLabelMapper;

    @Override
    public List<LabelVO> listLabels(Long projectId, Long userId) {
        checkProjectMember(projectId, userId);

        List<Label> labels = baseMapper.selectList(
                new LambdaQueryWrapper<Label>()
                        .eq(Label::getProjectId, projectId)
                        .orderByAsc(Label::getCreateTime));

        return labels.stream().map(this::toVO).toList();
    }

    @Override
    @Transactional
    public LabelVO createLabel(Long projectId, LabelCreateRequest request, Long userId) {
        checkProjectMember(projectId, userId);

        // 检查项目内标签名唯一
        // R-05-issue-3: 已修复 - insert外套try-catch捕获DuplicateKeyException→BusinessException(5001),并发创建同名标签时友好提示"标签名已存在"而非暴露数据库schema的500
        Long count = baseMapper.selectCount(
                new LambdaQueryWrapper<Label>()
                        .eq(Label::getProjectId, projectId)
                        .eq(Label::getName, request.getName()));
        if (count > 0) {
            throw new BusinessException(5001, "标签名已存在");
        }

        Label label = new Label();
        label.setProjectId(projectId);
        label.setName(request.getName());
        label.setColor(request.getColor() != null ? request.getColor() : "#409EFF");
        try {
            baseMapper.insert(label);
        } catch (DuplicateKeyException e) {
            throw new BusinessException(5001, "标签名已存在");
        }

        log.info("标签创建成功: name={}, projectId={}, color={}", request.getName(), projectId, label.getColor());

        return toVO(label);
    }

    @Override
    @Transactional
    public void deleteLabel(Long projectId, Long labelId, Long userId) {
        ProjectMember membership = checkProjectMember(projectId, userId);

        // member 不可删除标签
        if (!"owner".equals(membership.getRole())) {
            throw new BusinessException(5002, "无权限删除标签");
        }

        Label label = baseMapper.selectOne(
                new LambdaQueryWrapper<Label>()
                        .eq(Label::getId, labelId)
                        .eq(Label::getProjectId, projectId));
        if (label == null) {
            throw new BusinessException(5003, "标签不存在");
        }

        // 级联删除 task_label 关联
        taskLabelMapper.delete(
                new LambdaQueryWrapper<TaskLabel>()
                        .eq(TaskLabel::getLabelId, labelId));

        baseMapper.deleteById(labelId);

        log.info("标签已删除: id={}, name={}, projectId={}", labelId, label.getName(), projectId);
    }

    /** 校验用户是项目成员，返回成员记录 */
    // R-05-issue-2: 已修复 - 先查project表判断项目是否存在,不存在抛2001;存在但无membership抛2002,区分两条独立异常码对齐API_DESIGN §3.6
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

    private LabelVO toVO(Label label) {
        LabelVO vo = new LabelVO();
        vo.setId(label.getId());
        vo.setName(label.getName());
        vo.setColor(label.getColor());
        vo.setCreateTime(label.getCreateTime());
        return vo;
    }
}