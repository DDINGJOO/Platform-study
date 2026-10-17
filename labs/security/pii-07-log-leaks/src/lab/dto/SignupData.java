package lab.dto;

import lab.Pii;
import lombok.Data;

/** 아무것도 안 한 DTO. @Data 가 만든 toString 이 모든 필드를 찍는다. */
@Data
public class SignupData implements Signup {
    @Pii private String name;
    @Pii private String rrn;
    @Pii private String phone;
    private String channel;
}
