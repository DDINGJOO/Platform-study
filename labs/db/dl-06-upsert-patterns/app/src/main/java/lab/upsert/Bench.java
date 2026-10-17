package lab.upsert;

import java.security.SecureRandom;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.CyclicBarrier;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.atomic.AtomicInteger;

import org.springframework.core.retry.RetryPolicy;
import org.springframework.core.retry.RetryTemplate;

/**
 * 같은 키로 요청 4건을 동시에(배리어로 출발을 맞춰) 보내는 라운드를 N 번 돈다.
 * 연결 4개는 서로 다른 앱 인스턴스를 흉내 낸다(풀을 공유하지 않는다).
 */
public final class Bench {

    static final String HOST = "jdbc:mysql://127.0.0.1:39060/lab?useSSL=false&allowPublicKeyRetrieval=true";
    static final int WORKERS = 4;
    static final SecureRandom RND = new SecureRandom();

    static Connection open(String user, String pw, String extra) throws SQLException {
        return DriverManager.getConnection(HOST + extra, user, pw);
    }

    static Connection root() throws SQLException { return open("root", "labroot", ""); }

    static String randKey() {
        byte[] b = new byte[8];
        RND.nextBytes(b);
        return HexFormat.of().formatHex(b);
    }

    /** 표를 새로 만들고 무작위 키 1000행을 채운다. 새 키는 이 행들 사이 아무 갭에나 떨어진다. */
    static void reset() throws SQLException {
        try (Connection c = root(); Statement s = c.createStatement()) {
            s.execute("DROP TABLE IF EXISTS lab.visit");
            s.execute("""
                CREATE TABLE lab.visit (
                  id BIGINT AUTO_INCREMENT PRIMARY KEY,
                  user_key VARCHAR(32) NOT NULL,
                  payload VARCHAR(64) NOT NULL,
                  inserted_by VARCHAR(40) NOT NULL,
                  UNIQUE KEY uk_user_key (user_key)
                ) ENGINE=InnoDB""");
            c.setAutoCommit(false);
            try (PreparedStatement ps = c.prepareStatement("INSERT INTO lab.visit(user_key, payload, inserted_by) VALUES (?,?,?)")) {
                for (int i = 0; i < 1000; i++) {
                    ps.setString(1, randKey()); ps.setString(2, "seed"); ps.setString(3, "seed");
                    ps.addBatch();
                }
                ps.executeBatch();
            }
            c.commit();
        }
    }

    static long deadlockMetric(Connection r) throws SQLException {
        try (Statement s = r.createStatement();
             ResultSet rs = s.executeQuery("SELECT COUNT FROM information_schema.INNODB_METRICS WHERE NAME='lock_deadlocks'")) {
            return rs.next() ? rs.getLong(1) : -1;
        }
    }

    static long deadlockStatus(Connection r) throws SQLException {
        try (Statement s = r.createStatement();
             ResultSet rs = s.executeQuery("SHOW GLOBAL STATUS LIKE 'Innodb_deadlocks'")) {
            return rs.next() ? rs.getLong(2) : -1;   // 이 상태 변수가 없으면 -1
        }
    }

    record Result(String reqId, Patterns.Verdict verdict, Integer errorCode, long nanos, int attempts) {}

    static final class Wrapped extends RuntimeException {
        final SQLException sql;
        Wrapped(SQLException e) { super(e); this.sql = e; }
    }

    public static void run(String pattern, String iso, int rounds, boolean retry) throws Exception {
        reset();
        String extra = pattern.equals("p2a") ? "&useAffectedRows=true" : "";
        int level = iso.equals("RC") ? Connection.TRANSACTION_READ_COMMITTED : Connection.TRANSACTION_REPEATABLE_READ;

        List<Connection> conns = new ArrayList<>();
        for (int i = 0; i < WORKERS; i++) {
            Connection c = open("lab", "lab", extra);
            c.setAutoCommit(false);
            c.setTransactionIsolation(level);
            conns.add(c);
        }
        RetryTemplate retryTemplate = new RetryTemplate(RetryPolicy.builder()
                .predicate(t -> t instanceof Wrapped w && (w.sql.getErrorCode() == 1213 || w.sql.getErrorCode() == 1205))
                .maxRetries(3)
                .delay(Duration.ofMillis(20))
                .jitter(Duration.ofMillis(10))
                .build());

        Map<String, Integer> counts = new TreeMap<>();
        List<Long> lat = new ArrayList<>();
        int wrong = 0, correctRounds = 0, zeroRowRounds = 0, retried = 0, extraAttempts = 0;
        ExecutorService pool = Executors.newFixedThreadPool(WORKERS);
        try (Connection r = root()) {
            long dm0 = deadlockMetric(r), ds0 = deadlockStatus(r);
            for (int round = 0; round < rounds; round++) {
                String key = randKey();
                CyclicBarrier barrier = new CyclicBarrier(WORKERS);
                List<Future<Result>> fs = new ArrayList<>();
                for (int w = 0; w < WORKERS; w++) {
                    Connection c = conns.get(w);
                    String reqId = "r" + round + "-w" + w;
                    fs.add(pool.submit(() -> {
                        barrier.await();
                        long t0 = System.nanoTime();
                        AtomicInteger attempts = new AtomicInteger();
                        try {
                            Patterns.Verdict v;
                            if (retry) {
                                v = retryTemplate.invoke(() -> {
                                    attempts.incrementAndGet();
                                    return once(pattern, c, key, reqId);
                                });
                            } else {
                                attempts.incrementAndGet();
                                v = once(pattern, c, key, reqId);
                            }
                            return new Result(reqId, v, null, System.nanoTime() - t0, attempts.get());
                        } catch (RuntimeException e) {
                            Throwable x = e;
                            while (x != null && !(x instanceof Wrapped)) x = x.getCause();
                            int code = x instanceof Wrapped w2 ? w2.sql.getErrorCode() : -1;
                            if (code == -1) e.printStackTrace();
                            return new Result(reqId, null, code, System.nanoTime() - t0, attempts.get());
                        }
                    }));
                }
                List<Result> rs = new ArrayList<>();
                for (Future<Result> f : fs) rs.add(f.get());

                String insertedBy = null; int rows = 0;
                try (PreparedStatement ps = r.prepareStatement("SELECT inserted_by FROM lab.visit WHERE user_key=?")) {
                    ps.setString(1, key);
                    try (ResultSet q = ps.executeQuery()) { while (q.next()) { rows++; insertedBy = q.getString(1); } }
                }
                if (rows == 0) zeroRowRounds++;
                boolean roundOk = rows == 1;
                for (Result x : rs) {
                    lat.add(x.nanos);
                    if (x.attempts > 1) { retried++; extraAttempts += x.attempts - 1; }
                    if (x.verdict == null) {
                        counts.merge("fail_" + x.errorCode, 1, Integer::sum);
                        roundOk = false;
                        continue;
                    }
                    counts.merge(x.verdict.name(), 1, Integer::sum);
                    boolean ok = (x.verdict == Patterns.Verdict.SAVED && x.reqId.equals(insertedBy))
                            || (x.verdict == Patterns.Verdict.DUPLICATE && !x.reqId.equals(insertedBy));
                    if (!ok) { wrong++; roundOk = false; }
                }
                if (roundOk) correctRounds++;
            }
            long dm1 = deadlockMetric(r), ds1 = deadlockStatus(r);
            Collections.sort(lat);
            int fails = counts.entrySet().stream().filter(e -> e.getKey().startsWith("fail_")).mapToInt(Map.Entry::getValue).sum();
            System.out.printf("pattern=%s iso=%s retry=%s rounds=%d requests=%d%n", pattern, iso, retry, rounds, rounds * WORKERS);
            System.out.printf("  verdicts=%s%n", counts);
            System.out.printf("  failed=%d wrong_verdict=%d correct_rounds=%d/%d zero_row_rounds=%d%n", fails, wrong, correctRounds, rounds, zeroRowRounds);
            System.out.printf("  Innodb_deadlocks status before=%d after=%d%n", ds0, ds1);
            System.out.printf("  lock_deadlocks+=%d Innodb_deadlocks+=%d retried_requests=%d extra_attempts=%d%n", dm1 - dm0, ds1 - ds0, retried, extraAttempts);
            System.out.printf("  latency_ms p50=%.1f p99=%.1f max=%.1f%n", pct(lat, 0.50), pct(lat, 0.99), lat.get(lat.size() - 1) / 1e6);
        } finally {
            pool.shutdownNow();
            for (Connection c : conns) c.close();
        }
    }

    static Patterns.Verdict once(String pattern, Connection c, String key, String reqId) {
        try {
            return Patterns.run(pattern, c, key, "v1", reqId, Patterns.Step.NONE);
        } catch (SQLException e) {
            try { c.rollback(); } catch (SQLException ignore) {}
            throw new Wrapped(e);
        }
    }

    static double pct(List<Long> sorted, double p) {
        int i = (int) Math.ceil(p * sorted.size()) - 1;
        return sorted.get(Math.max(0, i)) / 1e6;
    }
}
