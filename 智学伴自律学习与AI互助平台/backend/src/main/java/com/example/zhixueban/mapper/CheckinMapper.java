package com.example.zhixueban.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.example.zhixueban.entity.Checkin;
import org.apache.ibatis.annotations.Mapper;

import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;
import java.util.Map;

@Mapper
public interface CheckinMapper extends BaseMapper<Checkin> {

    @Select("SELECT c.user_id AS userId, CAST(COUNT(c.id) AS SIGNED) AS totalScore " +
            "FROM checkin c " +
            "WHERE c.status = 1 " +
            "GROUP BY c.user_id " +
            "ORDER BY totalScore DESC " +
            "LIMIT #{limit}")
    List<Map<String, Object>> countCheckinByUser(@Param("limit") int limit);

    @Select("SELECT CAST(COUNT(c.id) AS SIGNED) " +
            "FROM checkin c " +
            "WHERE c.status = 1 AND c.user_id = #{userId}")
    Integer countCheckinForUser(@Param("userId") Long userId);
}
