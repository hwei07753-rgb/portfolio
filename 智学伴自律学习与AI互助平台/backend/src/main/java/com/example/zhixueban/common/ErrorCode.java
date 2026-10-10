package com.example.zhixueban.common;

/**
 * 业务错误码枚举定义（对齐总体设计说明书 §3.2）
 */
public enum ErrorCode {

    // 1xxx 用户与认证模块
    UNAUTHORIZED(1001, "未登录或登录已过期"),
    FORBIDDEN(1002, "无权进行该操作"),
    PARAM_ERROR(1003, "参数校验失败"),
    USER_BANNED(1004, "当前账号已被封禁"),
    WX_LOGIN_FAILED(1005, "微信登录鉴权失败"),
    USER_NOT_FOUND(1006, "用户不存在"),
    ADMIN_NOT_FOUND(1007, "管理员账号不存在"),
    ADMIN_DISABLED(1008, "管理员账号已禁用"),
    ADMIN_LOGIN_FAILED(1009, "账号或密码错误"),
    CONTENT_SENSITIVE(1201, "内容包含敏感词，请修改后重试"),

    // 2xxx 番茄钟与打卡模块
    CHECKIN_CONTENT_EMPTY(2001, "打卡心得内容不能为空"),
    CHECKIN_ALREADY_DONE(2002, "今日已打卡，请勿重复提交"),

    // 3xxx 社区互助与悬赏模块
    POST_NOT_FOUND(3001, "帖子不存在"),
    POST_DELETE_FORBIDDEN(3002, "无权删除该帖子"),
    POST_ALREADY_DELETED(3003, "帖子已被删除"),
    POST_ALREADY_SOLVED(3004, "该求助悬赏已结案，无法重复采纳"),
    INSUFFICIENT_COINS(3005, "自律积分不足以支付悬赏金币"),
    REPLY_NOT_FOUND(3006, "回复记录不存在"),
    CANNOT_ADOPT_OWN_REPLY(3007, "不能采纳自己的回复为最佳答案"),

    // 5xxx 系统全局错误
    SYSTEM_ERROR(500, "系统内部繁忙，请稍后再试");

    private final Integer code;
    private final String message;

    ErrorCode(Integer code, String message) {
        this.code = code;
        this.message = message;
    }

    public Integer getCode() {
        return code;
    }

    public String getMessage() {
        return message;
    }
}
