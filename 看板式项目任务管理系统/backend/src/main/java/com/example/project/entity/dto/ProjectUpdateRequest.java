package com.example.project.entity.dto;

import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
public class ProjectUpdateRequest {

    // R-05-issue-5: 已修复 - name为可选字段(仅归档时不传)，@Size仅设max=100不对null生效，语义清晰无歧义
    @Size(max = 100, message = "项目名称不能超过100字符")
    private String name;

    private Boolean archived;
}