package com.example.zhixueban.interceptor;

import com.example.zhixueban.common.Result;
import com.example.zhixueban.util.JwtUtils;
import com.example.zhixueban.util.UserContext;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.jsonwebtoken.Claims;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

@Component
public class LoginInterceptor implements HandlerInterceptor {

    private final JwtUtils jwtUtils;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public LoginInterceptor(JwtUtils jwtUtils) {
        this.jwtUtils = jwtUtils;
    }

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        // 放行 OPTIONS 请求
        if ("OPTIONS".equalsIgnoreCase(request.getMethod())) {
            return true;
        }

        String authHeader = request.getHeader("Authorization");
        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            sendUnauthorizedResponse(response, "未提供认证令牌，请先登录");
            return false;
        }

        String token = authHeader.substring(7).trim();
        if (!jwtUtils.validateToken(token)) {
            sendUnauthorizedResponse(response, "登录已过期或凭证无效，请重新登录");
            return false;
        }

        Claims claims = jwtUtils.parseToken(token);
        Long userId = Long.valueOf(claims.getSubject());
        Integer role = claims.get("role", Integer.class);

        request.setAttribute("userId", userId);
        request.setAttribute("role", role);

        UserContext.setUserId(userId);
        UserContext.setRole(role);

        return true;
    }

    @Override
    public void afterCompletion(HttpServletRequest request, HttpServletResponse response, Object handler, Exception ex) {
        UserContext.clear();
    }

    private void sendUnauthorizedResponse(HttpServletResponse response, String message) throws Exception {
        response.setContentType("application/json;charset=UTF-8");
        response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
        Result<Void> errorResult = Result.error(401, message);
        objectMapper.writeValue(response.getWriter(), errorResult);
    }
}
