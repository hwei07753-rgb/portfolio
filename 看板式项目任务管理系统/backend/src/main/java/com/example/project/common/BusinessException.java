package com.example.project.common;

/**
 * 业务异常类 —— Service 层抛此异常携带业务异常码(1xxx-9xxx),
 * 由 GlobalExceptionHandler 统一处理 → Result.error(code, message)
 */
public class BusinessException extends RuntimeException {

    private final Integer code;

    public BusinessException(Integer code, String message) {
        super(message);
        this.code = code;
    }

    public Integer getCode() {
        return code;
    }
}