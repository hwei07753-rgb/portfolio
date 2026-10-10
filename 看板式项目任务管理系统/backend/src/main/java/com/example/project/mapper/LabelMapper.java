package com.example.project.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.example.project.entity.Label;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface LabelMapper extends BaseMapper<Label> {
}