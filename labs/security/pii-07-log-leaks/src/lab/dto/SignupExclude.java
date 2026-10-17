package lab.dto;

import lab.Pii;
import lombok.Data;
import lombok.ToString;

/** 주민번호에만 @ToString.Exclude. 나중에 붙은 phone 과 name 은 잊었다. */
@Data
public class SignupExclude implements Signup {
    @Pii private String name;
    @Pii @ToString.Exclude private String rrn;
    @Pii private String phone;
    private String channel;
}
