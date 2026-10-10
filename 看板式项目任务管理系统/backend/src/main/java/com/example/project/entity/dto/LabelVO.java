package com.example.project.entity.dto;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class LabelVO {

    private Long id;

    private String name;

    private String color;

    private LocalDateTime createTime;
}