package lab;

import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.Base64;
import javax.crypto.Cipher;
import javax.crypto.Mac;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;

/**
 * 실습 전용 컬럼 암호화. 실무에 복사하지 말 것.
 * 유니크 제약을 걸 수 있게 같은 평문이 같은 암호문이 되도록 IV 를 평문의 HMAC 에서 뽑는다(결정적 암호화).
 * HMAC 키와 AES 키는 서로 다른 값으로 나눴지만, 둘 다 소스에 박힌 실습용 값이다.
 * 실무에서 결정적 암호화가 필요하면 AES-GCM-SIV(RFC 8452) 같은 정식 구성과 키 관리 체계를 쓴다.
 */
public final class LabCrypto {
    private static final byte[] ENC_KEY = "lab-only-enc-key-0123456789abcd!".getBytes(StandardCharsets.US_ASCII);
    private static final byte[] MAC_KEY = "lab-only-mac-key-0123456789abcd!".getBytes(StandardCharsets.US_ASCII);
    private static final String PREFIX = "LABENC:";
    private LabCrypto() {}

    public static String encrypt(String plain) {
        try {
            byte[] p = plain.getBytes(StandardCharsets.UTF_8);
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(MAC_KEY, "HmacSHA256"));
            byte[] iv = Arrays.copyOf(mac.doFinal(p), 12);
            Cipher c = Cipher.getInstance("AES/GCM/NoPadding");
            c.init(Cipher.ENCRYPT_MODE, new SecretKeySpec(ENC_KEY, "AES"), new GCMParameterSpec(128, iv));
            byte[] ct = c.doFinal(p);
            byte[] out = new byte[iv.length + ct.length];
            System.arraycopy(iv, 0, out, 0, iv.length);
            System.arraycopy(ct, 0, out, iv.length, ct.length);
            return PREFIX + Base64.getEncoder().encodeToString(out);
        } catch (Exception e) {
            throw new IllegalStateException("실습 암호화 실패");
        }
    }
}
