package lab;

import com.sun.net.httpserver.HttpServer;
import java.nio.charset.StandardCharsets;
import java.sql.Connection;
import lab.dto.Signup;
import lab.dto.SignupAllow;
import lab.dto.SignupData;
import lab.dto.SignupExclude;
import lab.dto.SignupMasked;
import lab.dto.SignupRecord;
import lab.repo.Db;
import lab.repo.LeakyMemberRepo;
import lab.repo.MemberRepo;
import lab.repo.SafeMemberRepo;
import lab.web.VerifyServer;
import org.apache.hc.client5.http.classic.methods.HttpPost;
import org.apache.hc.client5.http.impl.classic.CloseableHttpClient;
import org.apache.hc.client5.http.impl.classic.HttpClients;
import org.apache.hc.core5.http.ContentType;
import org.apache.hc.core5.http.io.entity.EntityUtils;
import org.apache.hc.core5.http.io.entity.StringEntity;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * 다섯 경로를 한 번씩 지나간다. 무엇을 켜고 끌지는 시스템 속성으로 고른다.
 *   -Ddto=data|exclude|masked|allow   ① 에 쓰는 DTO
 *   -Dcode=leaky|safe                 ①②③ 을 쓰는 코드 규칙 (DTO 통째 로깅, 예외 메시지, 원인 예외)
 * 로깅 레이어 쪽(마스킹 패턴, TurboFilter, wire 로거 수준)은 conf/logback.xml 의 속성으로 고른다.
 */
public final class Lab {
    private static final Logger log = LoggerFactory.getLogger("app");
    static final int PORT = 38070;

    public static void main(String[] args) throws Exception {
        String dto = System.getProperty("dto", "data");
        boolean safe = "safe".equals(System.getProperty("code", "leaky"));

        mark(1, "DTO 를 통째로 로깅");
        Signup s = switch (dto) {
            case "exclude" -> new SignupExclude();
            case "masked" -> new SignupMasked();
            case "allow" -> new SignupAllow();
            default -> new SignupData();
        };
        s.setName(Fake.NAME); s.setRrn(Fake.RRN); s.setPhone(Fake.PHONE); s.setChannel("web");
        SignupRecord r = new SignupRecord(Fake.NAME, Fake.RRN, Fake.PHONE, "web");
        if (safe) {
            log.info("가입 요청 channel={} requestId={}", "web", "req-0001");
        } else {
            log.info("가입 요청 {}", s);
            log.info("가입 요청(record) {}", r);
        }

        mark(2, "예외 메시지에 값을 실음");
        String typo = "000000 9876543";
        try {
            if (safe) Validators.safeRrn(typo); else Validators.leakyRrn(typo);
        } catch (IllegalArgumentException e) {
            log.warn("요청 거부", e);
        }

        mark(3, "원인 예외와 DB 유니크 제약 위반 메시지");
        try (Connection c = Db.open()) {
            MemberRepo repo = safe ? new SafeMemberRepo(c) : new LeakyMemberRepo(c);
            repo.insert(Fake.RRN, Fake.PHONE);
            try { repo.insert("000000-9876544", Fake.PHONE); }      // 전화번호 중복 (평문 컬럼)
            catch (RuntimeException e) { log.error("가입 실패", e); }
            try { repo.insert(Fake.RRN, "010-0000-0001"); }          // 주민번호 중복 (암호화 컬럼)
            catch (RuntimeException e) { log.error("가입 실패", e); }
        }

        mark(4, "HTTP 클라이언트의 요청·응답 덤프");
        HttpServer server = VerifyServer.start(PORT);
        try (CloseableHttpClient http = HttpClients.createDefault()) {
            HttpPost post = new HttpPost("http://127.0.0.1:" + PORT + "/verify");
            post.setEntity(new StringEntity("{\"name\":\"" + Fake.NAME + "\",\"rrn\":\"" + Fake.RRN
                    + "\",\"phone\":\"" + Fake.PHONE + "\"}", ContentType.APPLICATION_JSON));
            String res = http.execute(post, rsp -> EntityUtils.toString(rsp.getEntity(), StandardCharsets.UTF_8));
            log.info("본인확인 응답 수신 length={}", res.length());
        } finally {
            server.stop(0);
        }

        mark(5, "마스킹 정규식이 놓치는 입력");
        String fullWidth = toFullWidth(Fake.RRN);
        String[] inputs = {
            Fake.RRN,                       // 표준 형식
            "000000 9876543",               // 구분자가 공백
            "000000–9876543",          // 구분자가 en dash (U+2013)
            fullWidth,                      // 전각 숫자
            "000000" + "9876543",           // 구분자 없이 13자리
            "뒷자리 9876543",               // 뒷자리 7자리만
            "010 0000 0000",                // 전화번호, 공백
            "010.0000.0000",                // 전화번호, 점
            "011-000-0000",                 // 010 이 아닌 번호, 국번 3자리
            "/search?q=010%200000%200000",  // URL 인코딩된 공백
        };
        for (String q : inputs) log.info("검색 q={}", q);
        System.out.println("### END");
    }

    private static void mark(int n, String title) { System.out.println("### P" + n + " " + title); }

    private static String toFullWidth(String v) {
        StringBuilder b = new StringBuilder();
        for (char ch : v.toCharArray()) b.append(ch >= '0' && ch <= '9' ? (char) (ch - '0' + '０') : ch);
        return b.toString();
    }
}
