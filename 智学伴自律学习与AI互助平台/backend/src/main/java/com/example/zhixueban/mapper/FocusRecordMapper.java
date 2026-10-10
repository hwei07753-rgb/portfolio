package com.example.zhixueban.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.example.zhixueban.entity.FocusRecord;
import org.apache.ibatis.annotations.Mapper;

import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Mapper
public interface FocusRecordMapper extends BaseMapper<FocusRecord> {

    @Select("SELECT f.user_id AS userId, CAST(COALESCE(SUM(f.duration_minutes), 0) AS SIGNED) AS totalScore " +
            "FROM focus_record f " +
            "WHERE f.status = 0 AND f.start_time >= #{startTime} AND f.start_time <= #{endTime} " +
            "GROUP BY f.user_id " +
            "ORDER BY totalScore DESC " +
            "LIMIT #{limit}")
    List<Map<String, Object>> sumDurationByUser(@Param("startTime") LocalDateTime startTime,
                                                @Param("endTime") LocalDateTime endTime,
                                                @Param("limit") int limit);

    @Select("SELECT CAST(COALESCE(SUM(f.duration_minutes), 0) AS SIGNED) " +
            "FROM focus_record f " +
            "WHERE f.status = 0 AND f.user_id = #{userId} AND f.start_time >= #{startTime} AND f.start_time <= #{endTime}")
    Integer sumDurationForUser(@Param("userId") Long userId,
                               @Param("startTime") LocalDateTime startTime,
                               @Param("endTime") LocalDateTime endTime);
}
