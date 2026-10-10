package com.example.zhixueban.enums;

import com.baomidou.mybatisplus.annotation.EnumValue;

public enum UserRoleEnum {
    STUDENT(0, "学员"),
    ADMIN(1, "管理员");

    @EnumValue
    private final Integer code;
    private final String desc;

    UserRoleEnum(Integer code, String desc) {
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
