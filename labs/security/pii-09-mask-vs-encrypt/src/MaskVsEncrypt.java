// 개인정보 암호화 9편 실습: 같은 입력에 마스킹, AES-GCM, HMAC 을 적용해
// (1) 원문으로 되돌릴 수 있나 (2) 같은 값이 같은 출력이 되나 (3) 키를 바꾸면 기존 값은 어떻게 되나
// 를 한 화면에 찍는다.
//
// 데이터는 전부 가짜다. 계좌번호는 999 로 시작하는 실습용 형식이고, 이름은 홍길동 하나뿐이다.
// 키는 실습용 문자열에서 만든 고정 키이며 어떤 운영 시스템의 키와도 관계없다.
// 이 프로그램은 토큰이나 암호문에서 원문을 역산하거나 후보를 대입하는 일을 하지 않는다.
//
// 실행: java src/MaskVsEncrypt.java        (JDK 11 이상, 외부 라이브러리 없음)

import javax.crypto.AEADBadTagException;
import javax.crypto.Cipher;
import javax.crypto.Mac;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class MaskVsEncrypt {

    // ---- 실습용 가짜 데이터 -------------------------------------------------
    // A 가 세 번, B 가 두 번, C 가 한 번. C 는 A 와 끝 여섯 자리가 같다(마스킹하면 겹치게 골랐다).
    static final String A = "999-00-000001";
    static final String B = "999-00-000002";
    static final String C = "999-77-000001";
    static final String[] ROWS = {A, B, A, C, A, B};

    // 이름과 번호가 한 문장에 섞인 자유 메모 (가짜)
    static final String SENTENCE = "메모: 홍길동 님이 알려 준 번호 999-00-000001 로 수정함";

    // ---- 실습용 키 (운영 키 아님) --------------------------------------------
    static final String PREFIX = "lab9";                       // 실습용 암호문 표시
    static final byte[] AES_K1 = key("lab9-aes-key-1");
    static final byte[] AES_K2 = key("lab9-aes-key-2");
    static final byte[] MAC_K1 = key("lab9-hmac-key-1");
    static final byte[] MAC_K2 = key("lab9-hmac-key-2");
    static final SecureRandom RND = new SecureRandom();

    public static void main(String[] args) throws Exception {
        System.out.println("입력 6행: A B A C A B   (A=" + A + ", B=" + B + ", C=" + C + ")");
        System.out.println();

        // ---------------- (1)(2) 세 방식으로 바꿔 저장 ----------------
        List<String> masked = new ArrayList<>(), gcm = new ArrayList<>(), mac = new ArrayList<>();
        for (String v : ROWS) {
            masked.add(maskAccount(v));
            gcm.add(encrypt(AES_K1, "k1", v));
            mac.add(hmac(MAC_K1, v));
        }
        String[] names = {"A", "B", "A", "C", "A", "B"};
        System.out.println("[1] 저장되는 값 (앞 22자)");
        System.out.println("  행  저장용 마스킹   AES-GCM (k1)             HMAC-SHA256 (k1)");
        for (int i = 0; i < ROWS.length; i++) {
            System.out.printf("  %-3s %-15s %-24s %-24s%n", (i + 1) + names[i], masked.get(i),
                    cut(gcm.get(i), 22), cut(mac.get(i), 22));
        }
        System.out.println();

        // (1) 되돌리기
        int maskBack = 0, gcmBack = 0;
        for (int i = 0; i < ROWS.length; i++) {
            if (masked.get(i).equals(ROWS[i])) maskBack++;
            if (decrypt(AES_K1, gcm.get(i)).equals(ROWS[i])) gcmBack++;
        }
        System.out.println("[2] 원문으로 되돌린 행 (6행 중)");
        System.out.println("  저장용 마스킹 : " + maskBack + "   가린 자리의 숫자는 어디에도 남아 있지 않다");
        System.out.println("  AES-GCM       : " + gcmBack + "   k1 으로 복호화하면 원문과 같다");
        System.out.println("  HMAC          : -   복호화 연산이 없다. 원문을 아는 쪽이 다시 계산해 비교만 한다");
        System.out.println();

        // (2) 같은 값 -> 같은 출력?
        System.out.println("[3] 서로 다른 출력의 개수 (서로 다른 입력은 3개)");
        System.out.println("  저장용 마스킹 : " + distinct(masked) + "   A 와 C 가 같은 값이 된다");
        System.out.println("  AES-GCM       : " + distinct(gcm) + "   같은 A 세 번도 매번 다르다 (IV 를 행마다 새로 뽑음)");
        System.out.println("  HMAC          : " + distinct(mac) + "   같은 입력은 같은 토큰");
        System.out.println();

        // 등치 조회: A 를 찾는다
        String qMask = maskAccount(A), qMac = hmac(MAC_K1, A), qGcm = encrypt(AES_K1, "k1", A);
        System.out.println("[4] WHERE col = f(A) 로 찾은 행 (정답은 1,3,5행)");
        System.out.println("  저장용 마스킹 : " + hits(masked, qMask) + "   C(4행)까지 걸린다");
        System.out.println("  AES-GCM       : " + hits(gcm, qGcm) + "   새로 암호화한 A 는 저장된 어느 행과도 다르다");
        System.out.println("  HMAC          : " + hits(mac, qMac));
        System.out.println("  가장 많이 나온 출력의 빈도  마스킹 " + topFreq(masked) + " / GCM " + topFreq(gcm) + " / HMAC " + topFreq(mac)
                + "   (원문 기준 A 의 빈도는 3)");
        System.out.println();

        // ---------------- (3) 키를 바꾸면 ----------------
        System.out.println("[5] 키를 k1 에서 k2 로 바꾸면");
        int gcmFail = 0;
        for (String c : gcm) {
            try { decrypt(AES_K2, c); } catch (AEADBadTagException e) { gcmFail++; }
        }
        System.out.println("  AES-GCM: k2 로 기존 행 복호화 실패 " + gcmFail + "/6 (AEADBadTagException)");
        List<String> gcm2 = new ArrayList<>();
        for (String c : gcm) {
            String keyId = c.split("\\$")[1];
            byte[] old = keyId.equals("k1") ? AES_K1 : AES_K2;
            gcm2.add(encrypt(AES_K2, "k2", decrypt(old, c)));   // 키 ID 로 옛 키를 골라 풀고 새 키로 다시 싼다
        }
        int gcm2ok = 0;
        for (int i = 0; i < ROWS.length; i++) if (decrypt(AES_K2, gcm2.get(i)).equals(ROWS[i])) gcm2ok++;
        System.out.println("           옛 키로 풀어 k2 로 다시 암호화 6행 -> k2 로 복호화 성공 " + gcm2ok + "/6");
        System.out.println("           k1 을 버리기 전에 이 일을 끝내야 한다. k1 이 먼저 사라지면 6/6 이 영구히 읽히지 않는다");

        String qMac2 = hmac(MAC_K2, A);
        System.out.println("  HMAC   : k2 로 계산한 A 의 토큰으로 기존 행 조회 -> " + hits(mac, qMac2) + "   (k1 토큰과 다르다)");
        List<String> mac2 = new ArrayList<>();
        for (String c : gcm2) mac2.add(hmac(MAC_K2, decrypt(AES_K2, c)));  // 원문은 암호문 컬럼에서 꺼낸다
        System.out.println("           암호문 컬럼을 풀어 k2 토큰을 다시 계산 6행 -> 조회 " + hits(mac2, qMac2));
        System.out.println("           토큰만 저장했다면 원문이 다시 들어오기 전까지 계산할 재료가 없다");
        System.out.println("  마스킹 : 키가 없다. 바꿀 것도, 되살릴 것도 없다");
        System.out.println();

        // ---------------- 문장 안의 개인정보 ----------------
        System.out.println("[6] 자유 문장 하나 (가짜)");
        System.out.println("  원문          : " + SENTENCE);
        System.out.println("  정규식 마스킹 : " + maskInSentence(SENTENCE) + "   이름은 패턴에 없어서 그대로");
        String sc = encrypt(AES_K1, "k1", SENTENCE);
        System.out.println("  문장째 GCM    : " + cut(sc, 40) + "  (길이 " + sc.length() + "자, 원문 "
                + SENTENCE.length() + "자 = UTF-8 " + SENTENCE.getBytes(StandardCharsets.UTF_8).length + "바이트)");
        System.out.println("  권한자 화면   : " + decrypt(AES_K1, sc) + "   복호화 후 그대로 보여 줄 수 있다");
        System.out.println("  다른 화면     : " + maskInSentence(decrypt(AES_K1, sc)) + "   표시용 마스킹은 읽는 쪽에서 건다");
        System.out.println();

        System.out.println("[7] 저장 길이 (원문 계좌번호 " + A.length() + "자)");
        System.out.println("  저장용 마스킹 " + masked.get(0).length() + "자 / AES-GCM " + gcm.get(0).length()
                + "자 (IV 12B + 본문 + 태그 16B, Base64, 접두어 포함) / HMAC " + mac.get(0).length() + "자 (32B, Base64)");
    }

    // ---- 방식별 구현 -----------------------------------------------------------

    /** 앞 세 자리와 끝 두 자리만 남기고 숫자를 * 로. 하이픈 위치는 둔다. */
    static String maskAccount(String v) {
        StringBuilder sb = new StringBuilder();
        int digits = 0, total = (int) v.chars().filter(Character::isDigit).count();
        for (char ch : v.toCharArray()) {
            if (Character.isDigit(ch)) {
                digits++;
                sb.append(digits <= 3 || digits > total - 2 ? ch : '*');
            } else sb.append(ch);
        }
        return sb.toString();
    }

    static final Pattern ACCOUNT = Pattern.compile("\\d{3}-\\d{2}-\\d{6}");

    static String maskInSentence(String s) {
        Matcher m = ACCOUNT.matcher(s);
        StringBuilder sb = new StringBuilder();
        while (m.find()) m.appendReplacement(sb, maskAccount(m.group()));
        m.appendTail(sb);
        return sb.toString();
    }

    /** AES-256-GCM, 행마다 새 96비트 IV. 형식: lab9$키ID$Base64(IV || 암호문 || 태그) */
    static String encrypt(byte[] key, String keyId, String plain) throws Exception {
        byte[] iv = new byte[12];
        RND.nextBytes(iv);
        Cipher c = Cipher.getInstance("AES/GCM/NoPadding");
        c.init(Cipher.ENCRYPT_MODE, new SecretKeySpec(key, "AES"), new GCMParameterSpec(128, iv));
        c.updateAAD(keyId.getBytes(StandardCharsets.UTF_8));   // 키 ID 를 바꿔 끼우면 태그 검증에서 걸린다
        byte[] ct = c.doFinal(plain.getBytes(StandardCharsets.UTF_8));
        byte[] out = new byte[iv.length + ct.length];
        System.arraycopy(iv, 0, out, 0, iv.length);
        System.arraycopy(ct, 0, out, iv.length, ct.length);
        return PREFIX + "$" + keyId + "$" + Base64.getEncoder().encodeToString(out);
    }

    static String decrypt(byte[] key, String stored) throws Exception {
        String[] p = stored.split("\\$");
        byte[] all = Base64.getDecoder().decode(p[2]);
        Cipher c = Cipher.getInstance("AES/GCM/NoPadding");
        c.init(Cipher.DECRYPT_MODE, new SecretKeySpec(key, "AES"), new GCMParameterSpec(128, all, 0, 12));
        c.updateAAD(p[1].getBytes(StandardCharsets.UTF_8));
        return new String(c.doFinal(all, 12, all.length - 12), StandardCharsets.UTF_8);
    }

    /** HMAC-SHA256 토큰, Base64. 등치 조회용 별도 컬럼에 둔다. */
    static String hmac(byte[] key, String v) throws Exception {
        Mac m = Mac.getInstance("HmacSHA256");
        m.init(new SecretKeySpec(key, "HmacSHA256"));
        return Base64.getEncoder().encodeToString(m.doFinal(v.getBytes(StandardCharsets.UTF_8)));
    }

    // ---- 보조 ------------------------------------------------------------------

    static byte[] key(String label) {
        try { return MessageDigest.getInstance("SHA-256").digest(label.getBytes(StandardCharsets.UTF_8)); }
        catch (Exception e) { throw new IllegalStateException(e); }
    }

    static int distinct(List<String> xs) { return new HashSet<>(xs).size(); }

    static int topFreq(List<String> xs) {
        Map<String, Integer> f = new HashMap<>();
        for (String x : xs) f.merge(x, 1, Integer::sum);
        return Collections.max(f.values());
    }

    static String hits(List<String> col, String q) {
        List<String> r = new ArrayList<>();
        for (int i = 0; i < col.size(); i++) if (col.get(i).equals(q)) r.add(String.valueOf(i + 1));
        return r.isEmpty() ? "없음" : String.join(",", r) + "행";
    }

    static String cut(String s, int n) { return s.length() <= n ? s : s.substring(0, n) + "…"; }
}
