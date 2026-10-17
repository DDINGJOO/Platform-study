package lab.dto;

import lab.Masking;
import lab.Pii;

/** record 에 toString 을 직접 선언한 판. ArchUnit 규칙 3 이 통과시키는지 보려고 둔다(로그 실행에는 쓰지 않는다). */
public record SignupRecordSafe(@Pii String name, @Pii String rrn, @Pii String phone, String channel) {
    @Override
    public String toString() {
        return "SignupRecordSafe[rrn=" + maskedRrn() + ", channel=" + channel + "]";
    }

    // toString 안에서 원본 필드를 직접 읽으면 규칙 1 에 걸린다. 마스킹 메서드를 거친다
    String maskedRrn() { return Masking.rrn(rrn); }
}
