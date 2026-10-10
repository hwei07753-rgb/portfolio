package com.example.project.entity.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class BurndownPoint {

    // R-05-issue-4: 已修复 - date改为LocalDate，Jackson自动ISO 8601序列化，类型安全
    private LocalDate date;

    private Integer remaining;
}