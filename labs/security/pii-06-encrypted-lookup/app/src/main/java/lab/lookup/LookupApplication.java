package lab.lookup;

import com.google.crypto.tink.DeterministicAead;
import com.google.crypto.tink.KeysetHandle;
import com.google.crypto.tink.RegistryConfiguration;
import com.google.crypto.tink.daead.PredefinedDeterministicAeadParameters;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

import java.security.SecureRandom;
import java.util.*;
import java.util.function.Supplier;
import java.util.stream.Collectors;

/**
 * 사용법: java -jar lookup.jar <mode> [인자]
 *   seed <행 수>   테이블을 새로 만들고 가짜 데이터를 넣는다(사람 수 = 행 수 / 10, 빈도는 일부러 치우치게)
 *   demo           세 방식의 findBy 결과 행 수와 LIKE
 *   bench <반복>   조회 시간과 EXPLAIN
 *   freq           GROUP BY 로 보이는 빈도
 *   rotate         키 회전 비용과 회전 도중의 조회
 *   ivreuse        GCM 에서 IV 를 고정하면 생기는 일
 */
@SpringBootApplication
public class LookupApplication implements CommandLineRunner {
    private final ClaimRepository repo;
    private final JdbcTemplate jdbc;
    private final TransactionTemplate tx;

    public LookupApplication(ClaimRepository repo, JdbcTemplate jdbc, PlatformTransactionManager tm) {
        this.repo = repo; this.jdbc = jdbc; this.tx = new TransactionTemplate(tm);
    }

    public static void main(String[] args) { System.exit(SpringApplication.exit(SpringApplication.run(LookupApplication.class, args))); }

    static String ssnOf(int person) { return String.format("000000-0%06d", person); }   // 생년월일 000000: 명백한 가짜

    @Override
    public void run(String... args) throws Exception {
        String mode = args.length > 0 ? args[0] : "demo";
        if (!mode.equals("seed") && !mode.equals("ivreuse")) LabKeys.load();
        switch (mode) {
            case "seed" -> seed(Integer.parseInt(args[1]));
            case "demo" -> demo();
            case "bench" -> bench(Integer.parseInt(args.length > 1 ? args[1] : "200"));
            case "freq" -> freq();
            case "rotate" -> rotate();
            case "ivreuse" -> ivreuse();
            default -> throw new IllegalArgumentException(mode);
        }
    }

    // ---------------------------------------------------------------- seed
    void seed(int rows) throws Exception {
        LabKeys.generateAndSave();
        int people = rows / 10;
        jdbc.execute("DROP TABLE IF EXISTS claim");
        jdbc.execute("""
            CREATE TABLE claim (
              id BIGINT AUTO_INCREMENT PRIMARY KEY,
              ssn_det    VARCHAR(80) NOT NULL,
              ssn_gcm    VARCHAR(80) NOT NULL,
              ssn_bidx   CHAR(64)    NOT NULL,
              ssn_bidx12 SMALLINT    NOT NULL,
              KEY idx_det (ssn_det), KEY idx_gcm (ssn_gcm), KEY idx_bidx (ssn_bidx), KEY idx_bidx12 (ssn_bidx12)
            ) ENGINE=InnoDB""");
        Random r = new Random(42);   // 데이터 분포는 매번 같다(키는 매번 새로)
        long t0 = System.nanoTime();
        List<Object[]> batch = new ArrayList<>();
        for (int i = 0; i < rows; i++) {
            int person = (int) (people * Math.pow(r.nextDouble(), 2));   // 앞 번호일수록 자주 나온다
            String ssn = ssnOf(person);
            batch.add(new Object[]{Crypto.detEncrypt(ssn), Crypto.gcmEncrypt(ssn), Crypto.bidx(ssn), Crypto.bidx12(ssn)});
            if (batch.size() == 2000) { insert(batch); batch.clear(); }
        }
        if (!batch.isEmpty()) insert(batch);
        jdbc.execute("ANALYZE TABLE claim");
        System.out.printf("seed rows=%d people=%d took=%.1fs%n", rows, people, (System.nanoTime() - t0) / 1e9);
    }

    void insert(List<Object[]> b) {
        tx.executeWithoutResult(st -> jdbc.batchUpdate("INSERT INTO claim (ssn_det, ssn_gcm, ssn_bidx, ssn_bidx12) VALUES (?,?,?,?)", b));
    }

    int rows() { return jdbc.queryForObject("SELECT COUNT(*) FROM claim", Integer.class); }

    /** 조회 대상: 사람 수의 한가운데 번호. 평균 7행 안팎이 나온다 */
    String target() { return ssnOf(rows() / 10 / 2); }

    int truthCount(String ssn) {   // 정답: 결정적 컬럼과 무관하게, 전 행을 복호화해서 센다
        return (int) jdbc.queryForList("SELECT ssn_gcm FROM claim", String.class).stream()
                .filter(c -> Crypto.gcmDecrypt(c).equals(ssn)).count();
    }

    // ---------------------------------------------------------------- demo
    void demo() {
        String ssn = target();
        System.out.printf("rows=%d  target=%s  (정답 %d행: 전 행 복호화로 센 값)%n%n", rows(), ssn, truthCount(ssn));
        System.out.println("같은 평문을 컨버터에 두 번 넣으면");
        System.out.printf("  ① det  %s%n         %s%n", Crypto.detEncrypt(ssn), Crypto.detEncrypt(ssn));
        System.out.printf("  ② gcm  %s%n         %s%n%n", Crypto.gcmEncrypt(ssn), Crypto.gcmEncrypt(ssn));
        System.out.printf("① repo.findBySsnDet(\"%s\")      -> %d행%n", ssn, repo.findBySsnDet(ssn).size());
        System.out.printf("② repo.findBySsnGcm(\"%s\")      -> %d행%n", ssn, repo.findBySsnGcm(ssn).size());
        long t = System.nanoTime();
        long n = repo.findAll().stream().filter(c -> ssn.equals(c.getSsnGcm())).count();
        System.out.printf("② repo.findAll() 후 앱에서 filter   -> %d행 (전 행 %d개 복호화, %.0fms)%n", n, rows(), (System.nanoTime() - t) / 1e6);
        System.out.printf("③ repo.findBySsnBidx(bidx(ssn))   -> %d행%n%n", repo.findBySsnBidx(Crypto.bidx(ssn)).size());
        String prefix = ssn.substring(0, 12);
        System.out.printf("LIKE: repo.findBySsnDetStartingWith(\"%s\") -> %d행 (평문 기준 정답 %d행)%n", prefix,
                repo.findBySsnDetStartingWith(prefix).size(),
                jdbc.queryForList("SELECT ssn_gcm FROM claim", String.class).stream().filter(c -> Crypto.gcmDecrypt(c).startsWith(prefix)).count());
    }

    // ---------------------------------------------------------------- bench
    record Stat(double p50, double p95, int resultRows) {}

    Stat time(int iters, Supplier<Integer> f) {
        for (int i = 0; i < Math.min(iters, 20); i++) f.get();   // 예열
        double[] ms = new double[iters];
        int n = 0;
        for (int i = 0; i < iters; i++) {
            long t = System.nanoTime();
            n = f.get();
            ms[i] = (System.nanoTime() - t) / 1e6;
        }
        Arrays.sort(ms);
        return new Stat(ms[iters / 2], ms[(int) Math.ceil(iters * 0.95) - 1], n);
    }

    void explain(String label, String sql, Object... params) {
        Map<String, Object> e = jdbc.queryForList("EXPLAIN " + sql, params).get(0);
        System.out.printf("  %-14s type=%-5s key=%-10s rows=%-7s Extra=%s%n", label, e.get("type"), e.get("key"), e.get("rows"), e.get("Extra"));
    }

    void bench(int iters) {
        String ssn = target();
        int scanIters = Math.max(5, iters / 40);
        int total = rows();
        String det = Crypto.detEncrypt(ssn), gcmArg = Crypto.gcmEncrypt(ssn), b = Crypto.bidx(ssn);
        short b12 = Crypto.bidx12(ssn);
        System.out.printf("rows=%d target=%s truth=%d iters=%d (scan iters=%d)%n", total, ssn, truthCount(ssn), iters, scanIters);
        System.out.println("EXPLAIN");
        explain("① det =", "SELECT * FROM claim WHERE ssn_det = ?", det);
        explain("② gcm =", "SELECT * FROM claim WHERE ssn_gcm = ?", gcmArg);
        explain("② full scan", "SELECT * FROM claim");
        explain("③ bidx =", "SELECT * FROM claim WHERE ssn_bidx = ?", b);
        explain("③' bidx12 =", "SELECT * FROM claim WHERE ssn_bidx12 = ?", b12);
        System.out.println("TIME (ms, p50 / p95, 결과 행)");
        Map<String, Stat> s = new LinkedHashMap<>();
        s.put("① findBySsnDet", time(iters, () -> repo.findBySsnDet(ssn).size()));
        s.put("② findBySsnGcm", time(iters, () -> repo.findBySsnGcm(ssn).size()));
        s.put("② findAll+filter", time(scanIters, () -> (int) repo.findAll().stream().filter(c -> ssn.equals(c.getSsnGcm())).count()));
        s.put("② JDBC 한 컬럼+복호화", time(scanIters, () -> (int) jdbc.queryForList("SELECT ssn_gcm FROM claim", String.class)
                .stream().filter(c -> Crypto.gcmDecrypt(c).equals(ssn)).count()));
        s.put("③ findBySsnBidx", time(iters, () -> repo.findBySsnBidx(Crypto.bidx(ssn)).size()));
        int[] cand = new int[1];
        s.put("③' bidx12+복호화 확인", time(iters, () -> {
            List<Claim> c = repo.findBySsnBidx12(Crypto.bidx12(ssn));
            cand[0] = c.size();
            return (int) c.stream().filter(x -> ssn.equals(x.getSsnGcm())).count();
        }));
        s.forEach((k, v) -> System.out.printf("  %-22s %8.2f / %8.2f   %d행%n", k, v.p50(), v.p95(), v.resultRows()));
        System.out.printf("  (③' 후보 %d행 중 진짜 %d행)%n", cand[0], s.get("③' bidx12+복호화 확인").resultRows());
        System.out.printf("CSV,%d,%s%n", total, s.entrySet().stream().map(e -> String.format("%s=%.2f/%.2f", e.getKey(), e.getValue().p50(), e.getValue().p95())).collect(Collectors.joining(",")));
    }

    // ---------------------------------------------------------------- freq
    void freq() {
        int total = rows();
        Map<String, Long> truth = jdbc.queryForList("SELECT ssn_gcm FROM claim", String.class).stream()
                .map(Crypto::gcmDecrypt).collect(Collectors.groupingBy(x -> x, Collectors.counting()));
        List<Long> top = truth.values().stream().sorted(Comparator.reverseOrder()).limit(5).toList();
        System.out.printf("rows=%d%n", total);
        System.out.printf("  %-26s distinct=%-6d top5=%s%n", "평문(정답, 키로 복호화)", truth.size(), top);
        for (String col : List.of("ssn_det", "ssn_bidx", "ssn_bidx12", "ssn_gcm")) {
            List<Map<String, Object>> g = jdbc.queryForList("SELECT " + col + " v, COUNT(*) c FROM claim GROUP BY " + col + " ORDER BY c DESC LIMIT 5");
            long distinct = jdbc.queryForObject("SELECT COUNT(DISTINCT " + col + ") FROM claim", Long.class);
            System.out.printf("  %-26s distinct=%-6d top5=%s%n", col + " (키 없이 SQL 만)", distinct,
                    g.stream().map(m -> ((Number) m.get("c")).longValue()).toList());
        }
        Map<String, Object> top1 = jdbc.queryForList("SELECT ssn_det v, COUNT(*) c FROM claim GROUP BY ssn_det ORDER BY c DESC LIMIT 1").get(0);
        String v = (String) top1.get("v");
        System.out.printf("%n가장 많은 ssn_det 값: %s... (%s행)%n", v.substring(0, 16), top1.get("c"));
        System.out.printf("  같은 행들의 ssn_gcm 앞 16자: %s%n", jdbc.queryForList("SELECT ssn_gcm FROM claim WHERE ssn_det = ? LIMIT 3", String.class, v)
                .stream().map(x -> x.substring(0, 16) + "...").toList());
    }

    // ---------------------------------------------------------------- rotate
    void rotate() throws Exception {
        String ssn = target();
        int total = rows();
        int truth = truthCount(ssn);
        long maxId = jdbc.queryForObject("SELECT MAX(id) FROM claim", Long.class);
        System.out.printf("rows=%d target=%s truth=%d%n", total, ssn, truth);

        // ① 결정적: 새 키를 주 키로 추가. 옛 키는 복호화용으로 남는다
        DeterministicAead oldDet = LabKeys.detPrimitive;
        KeysetHandle rotated = KeysetHandle.newBuilder(LabKeys.det)
                .addEntry(KeysetHandle.generateEntryFromParameters(PredefinedDeterministicAeadParameters.AES256_SIV).withRandomId().makePrimary())
                .build();
        LabKeys.setDet(rotated);
        long t = System.nanoTime();
        int moved = rewrite("ssn_det", maxId / 2, old -> Crypto.detEncrypt(Crypto.detDecrypt(old)));
        double half = (System.nanoTime() - t) / 1e9;
        String newCt = Crypto.detEncrypt(ssn), oldCt = Crypto.detEncrypt(oldDet, ssn);
        System.out.printf("%n① 결정적 키 회전, 절반(%d행) 옮긴 시점%n", moved);
        System.out.printf("  findBySsnDet (새 키로 인자 암호화)  -> %d행 / 정답 %d%n", repo.findBySsnDet(ssn).size(), truth);
        System.out.printf("  WHERE ssn_det = 옛 키 암호문          -> %d행%n", jdbc.queryForObject("SELECT COUNT(*) FROM claim WHERE ssn_det = ?", Integer.class, oldCt));
        System.out.printf("  WHERE ssn_det IN (새, 옛)            -> %d행%n", jdbc.queryForObject("SELECT COUNT(*) FROM claim WHERE ssn_det IN (?, ?)", Integer.class, newCt, oldCt));
        t = System.nanoTime();
        moved += rewrite("ssn_det", Long.MAX_VALUE, old -> Crypto.detEncrypt(Crypto.detDecrypt(old)));
        double detTotal = half + (System.nanoTime() - t) / 1e9;
        System.out.printf("  전부 옮긴 뒤 findBySsnDet -> %d행, 다시 쓴 행 %d, %.1fs%n", repo.findBySsnDet(ssn).size(), moved, detTotal);

        // ② 랜덤 IV: 키 번호가 암호문 안에 있으니 옛 행도 그대로 읽힌다. 조회에 걸린 것이 없다
        // 주의: 아래 시간(t)에는 절반 시점의 검증 출력(전 행 복호화)과 truthCount(전 행 복호화 한 번 더)가 들어 있다.
        //       그래서 ② 의 "전부 옮김" 시간은 다시 쓰기만의 시간보다 전 행 복호화 두 번만큼 길다
        LabKeys.oldGcmKey = LabKeys.gcmKey;
        byte[] nk = new byte[32]; new SecureRandom().nextBytes(nk);
        LabKeys.gcmKey = nk; LabKeys.gcmKeyId = 2;
        t = System.nanoTime();
        int g = rewrite("ssn_gcm", maxId / 2, old -> Crypto.gcmEncrypt(Crypto.gcmDecrypt(old)));
        System.out.printf("%n② 랜덤 IV 키 회전, 절반(%d행) 옮긴 시점: 전 행 복호화 %d행 성공, 정답 %d행 찾음%n", g,
                jdbc.queryForList("SELECT ssn_gcm FROM claim", String.class).stream().map(Crypto::gcmDecrypt).count(), truthCount(ssn));
        g += rewrite("ssn_gcm", Long.MAX_VALUE, old -> Crypto.gcmEncrypt(Crypto.gcmDecrypt(old)));
        System.out.printf("  전부 옮김: 다시 쓴 행 %d, %.1fs%n", g, (System.nanoTime() - t) / 1e9);

        // ③ 블라인드 인덱스: 암호화 키(ssn_gcm)는 ② 와 같다. 인덱스 키를 바꾸면 전 행의 HMAC 을 다시 계산한다
        byte[] oldIdx = LabKeys.idxKey;
        byte[] ni = new byte[32]; new SecureRandom().nextBytes(ni);
        LabKeys.idxKey = ni;
        t = System.nanoTime();
        int bi = rewriteBidx(maxId / 2);
        System.out.printf("%n③ 인덱스 키 회전, 절반(%d행) 옮긴 시점%n", bi);
        System.out.printf("  findBySsnBidx(새 키 HMAC)  -> %d행 / 정답 %d%n", repo.findBySsnBidx(Crypto.bidx(ssn)).size(), truth);
        System.out.printf("  findBySsnBidx(옛 키 HMAC)  -> %d행%n", repo.findBySsnBidx(Crypto.bidx(oldIdx, ssn)).size());
        bi += rewriteBidx(Long.MAX_VALUE);
        System.out.printf("  전부 옮김: 다시 쓴 행 %d, %.1fs (행마다 ssn_gcm 복호화 + HMAC)%n", bi, (System.nanoTime() - t) / 1e9);
    }

    /** id 순서로 1,000행씩 읽어 다시 쓴다. 이미 옮긴 행(lastId 이하)은 건너뛴다 */
    private long cursor = 0;
    private String cursorCol = "";

    int rewrite(String col, long untilId, java.util.function.UnaryOperator<String> f) {
        if (!col.equals(cursorCol)) { cursor = 0; cursorCol = col; }
        int n = 0;
        while (true) {
            List<Map<String, Object>> page = jdbc.queryForList("SELECT id, " + col + " v FROM claim WHERE id > ? AND id <= ? ORDER BY id LIMIT 1000", cursor, untilId);
            if (page.isEmpty()) return n;
            List<Object[]> up = new ArrayList<>();
            for (Map<String, Object> m : page) up.add(new Object[]{f.apply((String) m.get("v")), m.get("id")});
            tx.executeWithoutResult(st -> jdbc.batchUpdate("UPDATE claim SET " + col + " = ? WHERE id = ?", up));   // 1,000행마다 커밋
            cursor = ((Number) page.get(page.size() - 1).get("id")).longValue();
            n += page.size();
        }
    }

    int rewriteBidx(long untilId) {
        if (!"bidx".equals(cursorCol)) { cursor = 0; cursorCol = "bidx"; }
        int n = 0;
        while (true) {
            List<Map<String, Object>> page = jdbc.queryForList("SELECT id, ssn_gcm v FROM claim WHERE id > ? AND id <= ? ORDER BY id LIMIT 1000", cursor, untilId);
            if (page.isEmpty()) return n;
            List<Object[]> up = new ArrayList<>();
            for (Map<String, Object> m : page) {
                String plain = Crypto.gcmDecrypt((String) m.get("v"));
                up.add(new Object[]{Crypto.bidx(plain), Crypto.bidx12(plain), m.get("id")});
            }
            tx.executeWithoutResult(st -> jdbc.batchUpdate("UPDATE claim SET ssn_bidx = ?, ssn_bidx12 = ? WHERE id = ?", up));
            cursor = ((Number) page.get(page.size() - 1).get("id")).longValue();
            n += page.size();
        }
    }

    // ---------------------------------------------------------------- ivreuse
    void ivreuse() throws Exception {
        LabKeys.init();
        LabKeys.setDet(KeysetHandle.generateNew(PredefinedDeterministicAeadParameters.AES256_SIV));
        byte[] key = new byte[32]; new SecureRandom().nextBytes(key);
        byte[] fixedIv = new byte[12];   // "결정적으로 만들려고" IV 를 0 으로 고정한 GCM
        String a = ssnOf(1), b = ssnOf(735218);
        byte[] ca = Crypto.raw(Crypto.gcmEncryptWithIv(key, (byte) 1, fixedIv, a));
        byte[] cb = Crypto.raw(Crypto.gcmEncryptWithIv(key, (byte) 1, fixedIv, b));
        int len = a.length();
        byte[] xorCt = Crypto.xor(ca, cb, 13, len);
        byte[] xorPt = Crypto.xor(a.getBytes(), b.getBytes(), 0, len);
        System.out.printf("GCM, 키와 IV 고정, 평문 둘: %s / %s%n", a, b);
        System.out.printf("  암호문1 XOR 암호문2 = %s%n", HexFormat.ofDelimiter(" ").formatHex(xorCt));
        System.out.printf("  평문1   XOR 평문2   = %s%n", HexFormat.ofDelimiter(" ").formatHex(xorPt));
        byte[] rec = Crypto.xor(xorCt, a.getBytes(), 0, len);
        System.out.printf("  평문1을 아는 사람이 키 없이 복원한 평문2 = %s%n", new String(rec));
        System.out.printf("%nAES-SIV(결정적 AEAD) 같은 두 평문%n");
        byte[] sa = Crypto.raw(Crypto.detEncrypt(a)), sb = Crypto.raw(Crypto.detEncrypt(b));
        System.out.printf("  암호문1 XOR 암호문2 (접두어 5 + SIV 16바이트 뒤 본문) = %s%n", HexFormat.ofDelimiter(" ").formatHex(Crypto.xor(sa, sb, 5 + 16, len)));
        System.out.printf("  같은 평문 다시 암호화 == 처음 것? %s%n", Crypto.detEncrypt(a).equals(Crypto.detEncrypt(a)));
    }
}
