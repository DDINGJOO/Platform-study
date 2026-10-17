package lab.dto;

import lab.Pii;

/** 같은 값을 record 로 옮긴 것. Lombok 이 관여하지 않고, 컴파일러가 만든 toString 이 전부 찍는다. */
public record SignupRecord(@Pii String name, @Pii String rrn, @Pii String phone, String channel) {}
