package com.example.project.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.example.project.entity.Task;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;
import java.util.Map;

@Mapper
public interface TaskMapper extends BaseMapper<Task> {

    /** 按milestone_id批量统计未删除任务数（GROUP BY，替代逐条selectCount的N+1查询） */
    @Select("SELECT milestone_id AS milestoneId, COUNT(*) AS taskCount FROM task WHERE milestone_id IN (${milestoneIds}) AND status <> 'deleted' GROUP BY milestone_id")
    List<Map<String, Object>> countTasksByMilestoneIds(@Param("milestoneIds") String milestoneIds);
}