package com.example.zhixueban.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.example.zhixueban.entity.Post;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface PostMapper extends BaseMapper<Post> {
}
