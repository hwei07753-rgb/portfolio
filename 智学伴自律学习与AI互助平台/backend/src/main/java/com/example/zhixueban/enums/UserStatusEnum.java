package com.example.zhixueban.enums;

import com.baomidou.mybatisplus.annotation.EnumValue;

public enum UserStatusEnum {
    NORMAL(0, "正常"),
    BANNED(1, "封禁");

    @EnumValue
    private final Integer code;
    private final String desc;

    UserStatusEnum(Integer code, String desc) {
        this.code = code;
        this.desc = desc;
    }

    public Integer getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }
}
