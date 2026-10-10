package com.example.project.entity.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import lombok.Data;

import java.util.List;

@Data
public class MemberReplaceRequest {

    @NotEmpty(message = "成员列表不能为空")
    @Valid
    private List<MemberItem> members;

    @Data
    public static class MemberItem {

        @NotNull(message = "用户ID不能为空")
        private Long userId;

        @NotNull(message = "角色不能为空")
        @Pattern(regexp = "^(owner|member)$", message = "角色只能为 owner 或 member")
        private String role;
    }
}