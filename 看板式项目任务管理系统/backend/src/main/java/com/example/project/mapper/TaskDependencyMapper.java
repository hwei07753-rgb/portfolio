package com.example.project.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.example.project.entity.TaskDependency;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface TaskDependencyMapper extends BaseMapper<TaskDependency> {
}
