package com.example.zhixueban;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
@MapperScan("com.example.zhixueban.mapper")
public class ZhixuebanApplication {

    public static void main(String[] args) {
        SpringApplication.run(ZhixuebanApplication.class, args);
    }
}
