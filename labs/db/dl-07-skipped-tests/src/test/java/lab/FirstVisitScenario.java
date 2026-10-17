package lab;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

/**
 * 1편의 "첫 방문 동시 요청" 패턴.
 * 같은 키로 요청 N개가 동시에 들어와 각자 아래를 한다.
 *
 * buggy: 한 트랜잭션 안에서 INSERT IGNORE → SELECT ... FOR UPDATE → UPDATE → COMMIT
 *        (중복 키로 무시된 INSERT IGNORE 가 S 잠금을 남기고, FOR UPDATE 가 X 로 올리려다 서로 기다린다)
 * fixed: INSERT IGNORE 를 자동 커밋으로 먼저 끝내고, 그다음 트랜잭션에서 SELECT ... FOR UPDATE → UPDATE
 *        (FOR UPDATE 시점에 행이 이미 커밋돼 있고, 손에 쥔 S 잠금이 없다)
 */
public final class FirstVisitScenario {

    public record Result(int rounds, int threads, int ok, Map<String, Integer> errors, int wrongCounts) {
        public int failed() { return errors.values().stream().mapToInt(Integer::intValue).sum(); }
        @Override public String toString() {
            return "rounds=" + rounds + " threads=" + threads + " ok=" + ok + " failed=" + failed()
                    + " errors=" + errors + " wrongCounts=" + wrongCounts;
        }
    }

    private final String url, user, pass;

    public FirstVisitScenario(String url, String user, String pass) {
        this.url = url; this.user = user; this.pass = pass;
    }

    public void createTable() throws SQLException {
        try (Connection c = DriverManager.getConnection(url, user, pass); Statement s = c.createStatement()) {
            s.execute("DROP TABLE IF EXISTS first_visit");
            s.execute("CREATE TABLE first_visit (user_id BIGINT NOT NULL PRIMARY KEY, cnt INT NOT NULL)");
        }
    }

    public Result run(String impl, int rounds, int threads) throws Exception {
        List<Connection> conns = new ArrayList<>();
        for (int i = 0; i < threads; i++) conns.add(DriverManager.getConnection(url, user, pass));
        ExecutorService pool = Executors.newFixedThreadPool(threads);
        Map<String, Integer> errors = new TreeMap<>();
        int ok = 0;
        try {
            for (int r = 1; r <= rounds; r++) {
                long key = r;
                CountDownLatch ready = new CountDownLatch(threads);
                CountDownLatch start = new CountDownLatch(1);
                List<Future<String>> fs = new ArrayList<>();
                for (Connection c : conns) {
                    fs.add(pool.submit(() -> {
                        ready.countDown();
                        start.await();                 // 모두 준비된 뒤 한꺼번에 출발
                        try {
                            visit(c, impl, key);
                            return "ok";
                        } catch (SQLException e) {
                            try { c.rollback(); } catch (SQLException ignore) { }
                            return e.getSQLState() + "/" + e.getErrorCode();
                        }
                    }));
                }
                if (!ready.await(10, TimeUnit.SECONDS)) throw new IllegalStateException("workers not ready");
                start.countDown();
                for (Future<String> f : fs) {
                    String o = f.get(60, TimeUnit.SECONDS);
                    if (o.equals("ok")) ok++; else errors.merge(o, 1, Integer::sum);
                }
            }
        } finally {
            pool.shutdownNow();
            for (Connection c : conns) c.close();
        }
        return new Result(rounds, threads, ok, errors, wrongCounts(rounds, threads));
    }

    private static void visit(Connection c, String impl, long key) throws SQLException {
        if (impl.equals("fixed")) {
            c.setAutoCommit(true);
            insertIgnore(c, key);              // 자기 트랜잭션으로 바로 커밋
        }
        c.setAutoCommit(false);
        if (impl.equals("buggy")) insertIgnore(c, key);
        try (PreparedStatement ps = c.prepareStatement("SELECT cnt FROM first_visit WHERE user_id = ? FOR UPDATE")) {
            ps.setLong(1, key);
            try (ResultSet rs = ps.executeQuery()) { rs.next(); }
        }
        try (PreparedStatement ps = c.prepareStatement("UPDATE first_visit SET cnt = cnt + 1 WHERE user_id = ?")) {
            ps.setLong(1, key);
            ps.executeUpdate();
        }
        c.commit();
    }

    private static void insertIgnore(Connection c, long key) throws SQLException {
        try (PreparedStatement ps = c.prepareStatement("INSERT IGNORE INTO first_visit (user_id, cnt) VALUES (?, 0)")) {
            ps.setLong(1, key);
            ps.executeUpdate();
        }
    }

    /** 키마다 cnt 가 threads 와 같아야 한다. 아닌 키의 수. */
    private int wrongCounts(int rounds, int threads) throws SQLException {
        try (Connection c = DriverManager.getConnection(url, user, pass);
             PreparedStatement ps = c.prepareStatement("SELECT COUNT(*) FROM first_visit WHERE cnt <> ?")) {
            ps.setInt(1, threads);
            try (ResultSet rs = ps.executeQuery()) { rs.next(); return rs.getInt(1); }
        }
    }
}
