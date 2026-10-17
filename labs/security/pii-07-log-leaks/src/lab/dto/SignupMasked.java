package lab.dto;

import lab.Masking;
import lab.Pii;
import lombok.Data;
import lombok.ToString;

/** 원본 필드는 빼고, 같은 이름으로 마스킹한 값을 넣는다. */
@Data
public class SignupMasked implements Signup {
    @Pii @ToString.Exclude private String name;
    @Pii @ToString.Exclude private String rrn;
    @Pii @ToString.Exclude private String phone;
    private String channel;

    @ToString.Include(name = "name") String maskedName() { return Masking.name(name); }
    @ToString.Include(name = "rrn") String maskedRrn() { return Masking.rrn(rrn); }
    @ToString.Include(name = "phone") String maskedPhone() { return Masking.phone(phone); }
}
