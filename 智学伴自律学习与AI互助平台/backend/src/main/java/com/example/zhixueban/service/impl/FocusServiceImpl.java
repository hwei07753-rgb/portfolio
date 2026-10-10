package com.example.zhixueban.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.example.zhixueban.entity.FocusRecord;
import com.example.zhixueban.entity.FocusTag;
import com.example.zhixueban.entity.dto.FocusRecordRequest;
import com.example.zhixueban.entity.dto.FocusRecordVO;
import com.example.zhixueban.entity.dto.TodayStatsResponse;
import com.example.zhixueban.mapper.FocusRecordMapper;
import com.example.zhixueban.mapper.FocusTagMapper;
import com.example.zhixueban.service.FocusService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.util.List;

/**
 * 番茄钟专注服务实现
 */
@Service
public class FocusServiceImpl implements FocusService {

    private static final Logger log = LoggerFactory.getLogger(FocusServiceImpl.class);

    private final FocusRecordMapper focusRecordMapper;
    private final FocusTagMapper focusTagMapper;

    public FocusServiceImpl(FocusRecordMapper focusRecordMapper, FocusTagMapper focusTagMapper) {
        this.focusRecordMapper = focusRecordMapper;
        this.focusTagMapper = focusTagMapper;
    }

    @Override
    public FocusRecordVO record(Long userId, FocusRecordRequest request) {
        LocalDateTime endTime = request.getEndTime() != null ? request.getEndTime() : LocalDateTime.now();
        LocalDateTime startTime = request.getStartTime() != null
                ? request.getStartTime()
                : endTime.minusMinutes(request.getDurationMinutes());
        int status = request.getStatus() != null ? request.getStatus() : 0;

        FocusRecord record = FocusRecord.builder()
                .userId(userId)
                .durationMinutes(request.getDurationMinutes())
                .tag(request.getTag())
                .status(status)
                .startTime(startTime)
                .endTime(endTime)
                .build();
        focusRecordMapper.insert(record);
        log.info("专注记录已保存: userId={}, duration={}min, status={}", userId, record.getDurationMinutes(), status);
        return FocusRecordVO.fromEntity(record);
    }

    @Override
    public TodayStatsResponse todayStats(Long userId) {
        LocalDateTime dayStart = LocalDateTime.of(LocalDate.now(), LocalTime.MIN);
        LocalDateTime dayEnd = dayStart.plusDays(1);

        List<FocusRecord> todayRecords = focusRecordMapper.selectList(
                new LambdaQueryWrapper<FocusRecord>()
                        .eq(FocusRecord::getUserId, userId)
                        .ge(FocusRecord::getStartTime, dayStart)
                        .lt(FocusRecord::getStartTime, dayEnd)
        );

        int todayMinutes = todayRecords.stream()
                .filter(r -> r.getStatus() != null && r.getStatus() == 0)
                .mapToInt(r -> r.getDurationMinutes() != null ? r.getDurationMinutes() : 0)
                .sum();
        int completedCount = (int) todayRecords.stream()
                .filter(r -> r.getStatus() != null && r.getStatus() == 0)
                .count();

        return TodayStatsResponse.builder()
                .todayMinutes(todayMinutes)
                .todayCount(todayRecords.size())
                .completedCount(completedCount)
                .build();
    }

    @Override
    public List<FocusRecordVO> todayList(Long userId) {
        LocalDateTime dayStart = LocalDateTime.of(LocalDate.now(), LocalTime.MIN);
        LocalDateTime dayEnd = dayStart.plusDays(1);

        List<FocusRecord> records = focusRecordMapper.selectList(
                new LambdaQueryWrapper<FocusRecord>()
                        .eq(FocusRecord::getUserId, userId)
                        .ge(FocusRecord::getStartTime, dayStart)
                        .lt(FocusRecord::getStartTime, dayEnd)
                        .orderByDesc(FocusRecord::getStartTime)
        );
        return records.stream().map(FocusRecordVO::fromEntity).toList();
    }

    @Override
    public List<FocusTag> listTags() {
        return focusTagMapper.selectList(
                new LambdaQueryWrapper<FocusTag>()
                        .eq(FocusTag::getStatus, 1)
                        .orderByAsc(FocusTag::getSort)
        );
    }
}
