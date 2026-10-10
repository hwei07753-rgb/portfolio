package com.example.project.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.example.project.entity.Label;
import com.example.project.entity.dto.LabelCreateRequest;
import com.example.project.entity.dto.LabelVO;

import java.util.List;

public interface LabelService extends IService<Label> {

    List<LabelVO> listLabels(Long projectId, Long userId);

    LabelVO createLabel(Long projectId, LabelCreateRequest request, Long userId);

    void deleteLabel(Long projectId, Long labelId, Long userId);
}