package com.example.zhixueban.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.example.zhixueban.entity.User;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface UserMapper extends BaseMapper<User> {
}
