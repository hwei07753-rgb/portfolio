package com.example.project.entity.dto;

import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
public class TaskUnblockRequest {

    @Size(max = 500, message = "解阻说明不能超过500字符")
    private String comment;
}
