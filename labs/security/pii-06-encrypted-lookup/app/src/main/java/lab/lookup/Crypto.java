package lab.lookup;

import com.google.crypto.tink.DeterministicAead;

import javax.crypto.Cipher;
import javax.crypto.Mac;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.util.Arrays;
import java.util.Base64;
import java.util.HexFormat;

/** 세 방식의 암호 연산. 컨버터와 시드·회전 코드가 같은 함수를 쓴다. */
public final class Crypto {
    private static final SecureRandom RNG = new SecureRandom();
    private static final byte[] AD = "claim.ssn".getBytes(StandardCharsets.UTF_8);   // 연관 데이터: 이 컬럼용이라는 표시

    // ① 결정적: 같은 평문 -> 같은 암호문 (AES-SIV)
    public static String detEncrypt(String plain) { return detEncrypt(LabKeys.detPrimitive, plain); }

    public static String detEncrypt(DeterministicAead p, String plain) {
        try {
            return Base64.getEncoder().encodeToString(p.encryptDeterministically(plain.getBytes(StandardCharsets.UTF_8), AD));
        } catch (Exception e) { throw new IllegalStateException(e); }
    }

    public static String detDecrypt(String b64) {
        try {
            return new String(LabKeys.detPrimitive.decryptDeterministically(Base64.getDecoder().decode(b64), AD), StandardCharsets.UTF_8);
        } catch (Exception e) { throw new IllegalStateException(e); }
    }

    // ② 랜덤 IV: 매번 새 12바이트 IV (AES-GCM). 형식 = 키번호 1바이트 | IV 12 | 암호문+태그 16
    public static String gcmEncrypt(String plain) { return gcmEncrypt(LabKeys.gcmKey, LabKeys.gcmKeyId, plain); }

    public static String gcmEncrypt(byte[] key, byte keyId, String plain) {
        byte[] iv = new byte[12];
        RNG.nextBytes(iv);
        return gcmEncryptWithIv(key, keyId, iv, plain);
    }

    static String gcmEncryptWithIv(byte[] key, byte keyId, byte[] iv, String plain) {
        try {
            Cipher c = Cipher.getInstance("AES/GCM/NoPadding");
            c.init(Cipher.ENCRYPT_MODE, new SecretKeySpec(key, "AES"), new GCMParameterSpec(128, iv));
            c.updateAAD(AD);
            byte[] ct = c.doFinal(plain.getBytes(StandardCharsets.UTF_8));
            byte[] out = new byte[1 + 12 + ct.length];
            out[0] = keyId;
            System.arraycopy(iv, 0, out, 1, 12);
            System.arraycopy(ct, 0, out, 13, ct.length);
            return Base64.getEncoder().encodeToString(out);
        } catch (Exception e) { throw new IllegalStateException(e); }
    }

    public static String gcmDecrypt(String b64) {
        byte[] in = Base64.getDecoder().decode(b64);
        byte[] key = in[0] == LabKeys.gcmKeyId ? LabKeys.gcmKey : LabKeys.oldGcmKey;   // 키 번호로 키를 고른다
        try {
            Cipher c = Cipher.getInstance("AES/GCM/NoPadding");
            c.init(Cipher.DECRYPT_MODE, new SecretKeySpec(key, "AES"), new GCMParameterSpec(128, in, 1, 12));
            c.updateAAD(AD);
            return new String(c.doFinal(in, 13, in.length - 13), StandardCharsets.UTF_8);
        } catch (Exception e) { throw new IllegalStateException(e); }
    }

    // ③ 블라인드 인덱스: 정규화한 평문의 HMAC. 암호문과 별도 컬럼에 둔다
    public static String normalize(String ssn) { return ssn.replace("-", "").trim(); }

    public static byte[] hmac(byte[] key, String plain) {
        try {
            Mac m = Mac.getInstance("HmacSHA256");
            m.init(new SecretKeySpec(key, "HmacSHA256"));
            return m.doFinal(("claim.ssn|" + normalize(plain)).getBytes(StandardCharsets.UTF_8));
        } catch (Exception e) { throw new IllegalStateException(e); }
    }

    public static String bidx(String plain) { return bidx(LabKeys.idxKey, plain); }

    public static String bidx(byte[] key, String plain) { return HexFormat.of().formatHex(hmac(key, plain)); }

    /** 앞 12비트만 남긴 짧은 블라인드 인덱스(0~4095). 일부러 충돌을 낸다 */
    public static short bidx12(String plain) {
        byte[] h = hmac(LabKeys.idxKey, plain);
        return (short) (((h[0] & 0xff) << 4) | ((h[1] & 0xff) >>> 4));
    }

    static byte[] raw(String b64) { return Base64.getDecoder().decode(b64); }

    static byte[] xor(byte[] a, byte[] b, int from, int len) {
        byte[] o = new byte[len];
        for (int i = 0; i < len; i++) o[i] = (byte) (a[from + i] ^ b[from + i]);
        return o;
    }

    static byte[] slice(byte[] a, int from, int len) { return Arrays.copyOfRange(a, from, from + len); }

    private Crypto() {}
}
