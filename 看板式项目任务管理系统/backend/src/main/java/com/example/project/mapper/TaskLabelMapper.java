package com.example.project.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.example.project.entity.TaskLabel;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface TaskLabelMapper extends BaseMapper<TaskLabel> {
}