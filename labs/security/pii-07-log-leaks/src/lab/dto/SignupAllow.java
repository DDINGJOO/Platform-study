package lab.dto;

import lab.Pii;
import lombok.Data;
import lombok.ToString;

/** 허용 목록 방식. 표시한 것만 찍고, 새로 붙는 필드는 기본으로 빠진다. */
@Data
@ToString(onlyExplicitlyIncluded = true)
public class SignupAllow implements Signup {
    @Pii private String name;
    @Pii private String rrn;
    @Pii private String phone;
    @ToString.Include private String channel;
}
