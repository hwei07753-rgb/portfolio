package com.example.project.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.example.project.entity.Project;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;
import java.util.Map;

@Mapper
public interface ProjectMapper extends BaseMapper<Project> {

    @Select("SELECT COUNT(*) FROM task WHERE project_id = #{projectId} AND status != 'deleted'")
    int countTasksByProjectId(@Param("projectId") Long projectId);

    /** 批量统计项目任务数（R-05-issue-1 N+1优化） */
    // R-05-issue-1: 已修复 - 新增批量统计方法替代逐条countTasksByProjectId调用
    @Select("<script>SELECT project_id, COUNT(*) as cnt FROM task WHERE project_id IN <foreach collection='ids' item='id' open='(' separator=',' close=')'>#{id}</foreach> AND status != 'deleted' GROUP BY project_id</script>")
    List<Map<String, Object>> countTasksByProjectIds(@Param("ids") List<Long> projectIds);
}