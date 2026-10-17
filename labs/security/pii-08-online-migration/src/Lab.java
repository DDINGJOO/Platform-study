import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;

import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.io.IOException;
import java.io.OutputStream;
import java.io.PrintWriter;
import java.net.InetSocketAddress;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.SecureRandom;
import java.sql.*;
import java.util.*;
import java.util.concurrent.Executors;
import java.util.regex.Pattern;

/**
 * 8편 실습 앱 하나에 서버와 일회성 배치를 같이 넣었다.
 *
 *   serve  --port P --label v2 --read plain|lenient|strict --write plain|encrypt
 *   batch  fill [--select all|shape] [--page N] [--sleep-ms N]
 *   batch  restore [--page N] [--sleep-ms N]
 *   batch  verify
 *   batch  dump <파일>
 *
 * 암호문 형식과 키는 이 실습에서만 쓰는 값이다(LAB_KEY 환경변수, 접두어 "LABENC1:").
 */
public class Lab {

    // ------------------------------------------------------------------ 암복호
    static final String PREFIX = "LABENC1:";
    static final SecureRandom RNG = new SecureRandom();
    static SecretKeySpec key;

    static void initKey() {
        String b64 = System.getenv("LAB_KEY");
        if (b64 == null) throw new IllegalStateException("LAB_KEY 가 없다");
        key = new SecretKeySpec(Base64.getDecoder().decode(b64), "AES");
    }

    static String encrypt(String plain) {
        try {
            byte[] iv = new byte[12];
            RNG.nextBytes(iv);
            Cipher c = Cipher.getInstance("AES/GCM/NoPadding");
            c.init(Cipher.ENCRYPT_MODE, key, new GCMParameterSpec(128, iv));
            byte[] ct = c.doFinal(plain.getBytes(StandardCharsets.UTF_8));
            byte[] out = new byte[iv.length + ct.length];
            System.arraycopy(iv, 0, out, 0, iv.length);
            System.arraycopy(ct, 0, out, iv.length, ct.length);
            return PREFIX + Base64.getEncoder().encodeToString(out);
        } catch (Exception e) {
            throw new IllegalStateException("암호화 실패");
        }
    }

    static String decrypt(String stored) {
        try {
            byte[] all = Base64.getDecoder().decode(stored.substring(PREFIX.length()));
            Cipher c = Cipher.getInstance("AES/GCM/NoPadding");
            c.init(Cipher.DECRYPT_MODE, key, new GCMParameterSpec(128, all, 0, 12));
            return new String(c.doFinal(all, 12, all.length - 12), StandardCharsets.UTF_8);
        } catch (Exception e) {
            // 값은 메시지에 넣지 않는다
            throw new IllegalStateException("복호화 실패 (길이=" + stored.length() + ")");
        }
    }

    static boolean looksEncrypted(String v) {
        return v != null && v.startsWith(PREFIX);
    }

    // ------------------------------------------------------------------ 컨버터 (JPA AttributeConverter 와 같은 두 방향)
    interface Converter {
        String convertToDatabaseColumn(String attribute);
        String convertToEntityAttribute(String dbData);
    }

    /** 0단계: 암호화가 없는 원래 코드 */
    static final class PlainConverter implements Converter {
        public String convertToDatabaseColumn(String a) { return a; }
        public String convertToEntityAttribute(String d) { return d; }
    }

    /** 1~2단계: 평문과 암호문을 둘 다 읽는다. 쓰기는 스위치로 고른다 */
    static final class LenientConverter implements Converter {
        final boolean encryptOnWrite;
        LenientConverter(boolean encryptOnWrite) { this.encryptOnWrite = encryptOnWrite; }
        public String convertToDatabaseColumn(String a) {
            if (a == null) return null;
            return encryptOnWrite ? encrypt(a) : a;
        }
        public String convertToEntityAttribute(String d) {
            if (d == null) return null;
            return looksEncrypted(d) ? decrypt(d) : d;   // 암호문 모양이 아니면 아직 안 바뀐 평문으로 본다
        }
    }

    /** 5단계: 암호문만 읽는다. 평문이 남아 있으면 그 행을 읽는 요청이 실패한다 */
    static final class StrictConverter implements Converter {
        public String convertToDatabaseColumn(String a) { return a == null ? null : encrypt(a); }
        public String convertToEntityAttribute(String d) {
            if (d == null) return null;
            if (!looksEncrypted(d)) throw new IllegalStateException("암호문 형식이 아님 (길이=" + d.length() + ")");
            return decrypt(d);
        }
    }

    // ------------------------------------------------------------------ DB
    static String jdbcUrl() {
        return "jdbc:mysql://127.0.0.1:" + System.getenv().getOrDefault("LAB_DB_PORT", "38080")
                + "/lab?useSSL=false&allowPublicKeyRetrieval=true&characterEncoding=UTF-8"
                + "&connectionCollation=utf8mb4_0900_ai_ci&rewriteBatchedStatements=true";
    }

    static Connection connect() throws SQLException {
        return DriverManager.getConnection(jdbcUrl(), "lab", "labpass");
    }

    // ------------------------------------------------------------------ 서버
    static Converter conv;
    static final ThreadLocal<Connection> TL = new ThreadLocal<>();

    static Connection tlConn() throws SQLException {
        Connection c = TL.get();
        if (c == null || c.isClosed()) { c = connect(); TL.set(c); }
        return c;
    }

    record Agent(long id, String name, String rrn) {}

    static Agent load(Connection c, long id) throws SQLException {
        try (PreparedStatement ps = c.prepareStatement("SELECT id, name, rrn FROM agent WHERE id = ?")) {
            ps.setLong(1, id);
            try (ResultSet rs = ps.executeQuery()) {
                if (!rs.next()) return null;
                return new Agent(rs.getLong(1), rs.getString(2), conv.convertToEntityAttribute(rs.getString(3)));
            }
        }
    }

    static void serve(Map<String, String> o) throws Exception {
        int port = Integer.parseInt(o.get("port"));
        String label = o.getOrDefault("label", "?");
        String read = o.getOrDefault("read", "plain");
        String write = o.getOrDefault("write", "plain");
        initKey();
        conv = switch (read) {
            case "plain" -> new PlainConverter();
            case "lenient" -> new LenientConverter(write.equals("encrypt"));
            case "strict" -> new StrictConverter();
            default -> throw new IllegalArgumentException(read);
        };
        // 기동 로그: 파일에 적힌 값이 아니라 이 프로세스가 실제로 쓰는 값을 한 줄로 남긴다
        boolean enc = conv instanceof StrictConverter || (conv instanceof LenientConverter l && l.encryptOnWrite);
        System.out.println((enc ? "INFO " : "WARN ") + " started label=" + label + " port=" + port
                + " read=" + read + " encryptOnWrite=" + enc);

        HttpServer s = HttpServer.create(new InetSocketAddress("127.0.0.1", port), 512);
        s.setExecutor(Executors.newFixedThreadPool(12));
        s.createContext("/health", ex -> reply(ex, 200, "{\"label\":\"" + label + "\"}"));
        s.createContext("/agents", Lab::handle);
        s.start();
    }

    static void handle(HttpExchange ex) throws IOException {
        String path = ex.getRequestURI().getPath();
        Map<String, String> q = query(ex.getRequestURI().getRawQuery());
        try {
            Connection c = tlConn();
            String[] p = path.split("/");           // "", "agents", id, action
            if (p.length == 2) {                    // GET /agents?from=&limit=  목록 화면: 한 페이지를 한 번에 읽는다
                long from = Long.parseLong(q.get("from"));
                int limit = Integer.parseInt(q.getOrDefault("limit", "20"));
                StringBuilder sb = new StringBuilder("[");
                try (PreparedStatement ps = c.prepareStatement(
                        "SELECT id, rrn FROM agent WHERE id >= ? ORDER BY id LIMIT ?")) {
                    ps.setLong(1, from);
                    ps.setInt(2, limit);
                    try (ResultSet rs = ps.executeQuery()) {
                        boolean first = true;
                        while (rs.next()) {
                            String v = conv.convertToEntityAttribute(rs.getString(2));  // 한 행이 실패하면 페이지 전체가 실패
                            if (!first) sb.append(',');
                            first = false;
                            sb.append("{\"id\":").append(rs.getLong(1)).append(",\"rrn\":").append(json(v)).append('}');
                        }
                    }
                }
                reply(ex, 200, sb.append(']').toString());
                return;
            }
            long id = Long.parseLong(p[2]);
            if (p.length == 3) {                    // GET /agents/{id}
                Agent a = load(c, id);
                if (a == null) { reply(ex, 404, "{}"); return; }
                reply(ex, 200, "{\"id\":" + a.id() + ",\"rrn\":" + json(a.rrn()) + "}");
            } else if (p[3].equals("login")) {      // POST /agents/{id}/login  부분 갱신 없이 모든 컬럼을 다시 쓴다
                Agent a = load(c, id);
                try (PreparedStatement ps = c.prepareStatement(
                        "UPDATE agent SET name = ?, rrn = ?, last_login = NOW(6) WHERE id = ?")) {
                    ps.setString(1, a.name());
                    ps.setString(2, conv.convertToDatabaseColumn(a.rrn()));
                    ps.setLong(3, id);
                    ps.executeUpdate();
                }
                reply(ex, 200, "{}");
            } else if (p[3].equals("rrn")) {        // POST /agents/{id}/rrn?v=  값 자체를 바꾼다
                try (PreparedStatement ps = c.prepareStatement("UPDATE agent SET rrn = ? WHERE id = ?")) {
                    ps.setString(1, conv.convertToDatabaseColumn(q.get("v")));
                    ps.setLong(2, id);
                    ps.executeUpdate();
                }
                reply(ex, 200, "{}");
            } else {
                reply(ex, 404, "{}");
            }
        } catch (Exception e) {
            reply(ex, 500, "{\"error\":" + json(e.getClass().getSimpleName() + ": " + e.getMessage()) + "}");
        }
    }

    static void reply(HttpExchange ex, int code, String body) throws IOException {
        byte[] b = body.getBytes(StandardCharsets.UTF_8);
        ex.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        ex.sendResponseHeaders(code, b.length);
        try (OutputStream os = ex.getResponseBody()) { os.write(b); }
    }

    static Map<String, String> query(String raw) {
        Map<String, String> m = new HashMap<>();
        if (raw == null) return m;
        for (String kv : raw.split("&")) {
            int i = kv.indexOf('=');
            if (i > 0) m.put(kv.substring(0, i), URLDecoder.decode(kv.substring(i + 1), StandardCharsets.UTF_8));
        }
        return m;
    }

    static String json(String v) {
        if (v == null) return "null";
        StringBuilder sb = new StringBuilder("\"");
        for (char ch : v.toCharArray()) {
            switch (ch) {
                case '"' -> sb.append("\\\"");
                case '\\' -> sb.append("\\\\");
                default -> { if (ch < 0x20) sb.append(String.format("\\u%04x", (int) ch)); else sb.append(ch); }
            }
        }
        return sb.append('"').toString();
    }

    // ------------------------------------------------------------------ 배치
    /** 처음 데이터의 "정상 모양" 평문. shape 모드는 이 모양만 암호화한다 */
    static final Pattern SHAPE = Pattern.compile("^[0-9]{6}-?[0-9]{7}$");

    static void batch(String mode, Map<String, String> o, List<String> rest) throws Exception {
        initKey();
        try (Connection c = connect()) {
            switch (mode) {
                case "fill" -> rewrite(c, "fill", o);
                case "restore" -> rewrite(c, "restore", o);
                case "verify" -> verify(c);
                case "dump" -> dump(c, Path.of(rest.get(0)));
                default -> throw new IllegalArgumentException(mode);
            }
        }
    }

    /**
     * fill: 암호문이 아닌 값을 암호화한다(--select shape 이면 정상 모양 평문만).
     * restore: 암호문을 평문으로 되돌린다.
     * 한 페이지를 쓰고 같은 트랜잭션에서 진행 위치를 저장한다. 죽었다 다시 뜨면 그 다음 id 부터 읽는다.
     * UPDATE 는 "읽었던 값과 같을 때만" 건다. 그 사이 앱이 그 행을 고쳤으면 0행으로 끝난다.
     */
    static void rewrite(Connection c, String job, Map<String, String> o) throws Exception {
        int page = Integer.parseInt(o.getOrDefault("page", "1000"));
        long sleepMs = Long.parseLong(o.getOrDefault("sleep-ms", "0"));
        String select = o.getOrDefault("select", "all");
        c.setAutoCommit(false);
        long cursor = 0;
        try (PreparedStatement ps = c.prepareStatement("SELECT cursor_id FROM batch_state WHERE job = ?")) {
            ps.setString(1, job);
            try (ResultSet rs = ps.executeQuery()) { if (rs.next()) cursor = rs.getLong(1); }
        }
        c.commit();
        System.out.println("[" + job + "] start cursor=" + cursor + " select=" + select + " page=" + page);
        long t0 = System.nanoTime();
        long scanned = 0, written = 0, conflict = 0, skippedShape = 0, pages = 0;
        List<Long> shapeIds = new ArrayList<>();
        while (true) {
            List<long[]> ids = new ArrayList<>();
            List<String> vals = new ArrayList<>();
            try (PreparedStatement ps = c.prepareStatement(
                    "SELECT id, rrn FROM agent WHERE id > ? ORDER BY id LIMIT ?")) {
                ps.setLong(1, cursor);
                ps.setInt(2, page);
                try (ResultSet rs = ps.executeQuery()) {
                    while (rs.next()) { ids.add(new long[]{rs.getLong(1)}); vals.add(rs.getString(2)); }
                }
            }
            if (ids.isEmpty()) break;
            int batched = 0;
            try (PreparedStatement up = c.prepareStatement("UPDATE agent SET rrn = ? WHERE id = ? AND rrn = ?")) {
                for (int i = 0; i < ids.size(); i++) {
                    long id = ids.get(i)[0];
                    String v = vals.get(i);
                    scanned++;
                    if (v == null) continue;
                    String nv;
                    if (job.equals("fill")) {
                        if (looksEncrypted(v)) continue;
                        if (select.equals("shape") && !SHAPE.matcher(v).matches()) {
                            skippedShape++;
                            if (shapeIds.size() < 5) shapeIds.add(id);
                            continue;
                        }
                        nv = encrypt(v);
                        if (!decrypt(nv).equals(v)) throw new IllegalStateException("왕복 불일치 id=" + id);
                    } else {
                        if (!looksEncrypted(v)) continue;
                        nv = decrypt(v);
                    }
                    up.setString(1, nv);
                    up.setLong(2, id);
                    up.setString(3, v);
                    up.addBatch();
                    batched++;
                }
                if (batched > 0) {
                    for (int r : up.executeBatch()) {
                        if (r == 1 || r == Statement.SUCCESS_NO_INFO) written++; else conflict++;
                    }
                }
            }
            cursor = ids.get(ids.size() - 1)[0];
            try (PreparedStatement ps = c.prepareStatement(
                    "INSERT INTO batch_state (job, cursor_id, updated_at) VALUES (?, ?, NOW(6)) "
                            + "ON DUPLICATE KEY UPDATE cursor_id = VALUES(cursor_id), updated_at = NOW(6)")) {
                ps.setString(1, job);
                ps.setLong(2, cursor);
                ps.executeUpdate();
            }
            c.commit();
            pages++;
            if (pages % 50 == 0) System.out.println("[" + job + "] cursor=" + cursor + " written=" + written);
            if (sleepMs > 0) Thread.sleep(sleepMs);
        }
        try (PreparedStatement ps = c.prepareStatement("DELETE FROM batch_state WHERE job = ?")) {
            ps.setString(1, job);
            ps.executeUpdate();
        }
        c.commit();
        double sec = (System.nanoTime() - t0) / 1e9;
        System.out.printf("[%s] done scanned=%d written=%d conflict=%d skippedShape=%d pages=%d elapsed=%.1fs%n",
                job, scanned, written, conflict, skippedShape, pages, sec);
        if (!shapeIds.isEmpty()) System.out.println("[" + job + "] 모양이 달라 건너뛴 행 id 예: " + shapeIds);
    }

    /** 쓰지 않고 센다. SQL 로는 못 세는 "접두어만 맞고 풀리지 않는 값"까지 복호화로 가린다 */
    static void verify(Connection c) throws SQLException {
        long nul = 0, ok = 0, bad = 0, plain = 0, total = 0;
        List<Long> badIds = new ArrayList<>(), plainIds = new ArrayList<>();
        try (Statement st = c.createStatement(ResultSet.TYPE_FORWARD_ONLY, ResultSet.CONCUR_READ_ONLY)) {
            st.setFetchSize(Integer.MIN_VALUE);
            try (ResultSet rs = st.executeQuery("SELECT id, rrn FROM agent ORDER BY id")) {
                while (rs.next()) {
                    total++;
                    String v = rs.getString(2);
                    if (v == null) { nul++; continue; }
                    if (!looksEncrypted(v)) { plain++; if (plainIds.size() < 5) plainIds.add(rs.getLong(1)); continue; }
                    try { decrypt(v); ok++; } catch (IllegalStateException e) { bad++; if (badIds.size() < 5) badIds.add(rs.getLong(1)); }
                }
            }
        }
        System.out.printf("[verify] total=%d null=%d cipherOk=%d decryptFailed=%d notCipher=%d%n", total, nul, ok, bad, plain);
        if (!plainIds.isEmpty()) System.out.println("[verify] notCipher id 예: " + plainIds);
        if (!badIds.isEmpty()) System.out.println("[verify] decryptFailed id 예: " + badIds);
    }

    /** 부하 생성기가 "맞는 값"으로 쓸 기대값. 시작 시점(전부 평문)에만 뜬다 */
    static void dump(Connection c, Path out) throws Exception {
        try (Statement st = c.createStatement(ResultSet.TYPE_FORWARD_ONLY, ResultSet.CONCUR_READ_ONLY);
             PrintWriter w = new PrintWriter(Files.newBufferedWriter(out, StandardCharsets.UTF_8))) {
            st.setFetchSize(Integer.MIN_VALUE);
            try (ResultSet rs = st.executeQuery("SELECT id, rrn FROM agent ORDER BY id")) {
                while (rs.next()) w.println("{\"id\":" + rs.getLong(1) + ",\"rrn\":" + json(rs.getString(2)) + "}");
            }
        }
    }

    // ------------------------------------------------------------------ main
    public static void main(String[] args) throws Exception {
        Map<String, String> o = new HashMap<>();
        List<String> rest = new ArrayList<>();
        for (int i = 1; i < args.length; i++) {
            if (args[i].startsWith("--")) o.put(args[i].substring(2), args[++i]); else rest.add(args[i]);
        }
        switch (args[0]) {
            case "serve" -> serve(o);
            case "batch" -> batch(rest.remove(0), o, rest);
            default -> throw new IllegalArgumentException(args[0]);
        }
    }
}
