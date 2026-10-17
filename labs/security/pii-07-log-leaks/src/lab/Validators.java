package lab;

import java.util.regex.Pattern;

/** ② 예외 메시지 경로. 형식 검사는 바로 그 "형식이 틀린 값"을 들고 실패한다. */
public final class Validators {
    private static final Pattern RRN = Pattern.compile("\\d{6}-\\d{7}");
    private Validators() {}

    /** 새는 쪽: 받은 값을 메시지에 그대로 싣는다. */
    public static void leakyRrn(String v) {
        if (!RRN.matcher(v).matches()) {
            throw new IllegalArgumentException("주민번호 형식이 아닙니다: " + v);
        }
    }

    /** 막은 쪽: 어느 필드가 왜 틀렸는지와 길이만 싣는다. */
    public static void safeRrn(String v) {
        if (!RRN.matcher(v).matches()) {
            throw new IllegalArgumentException("주민번호 형식이 아닙니다 (field=rrn, length=" + v.length() + ")");
        }
    }
}
