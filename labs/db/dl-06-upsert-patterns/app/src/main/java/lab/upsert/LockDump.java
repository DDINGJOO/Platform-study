package lab.upsert;

import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

/**
 * performance_schema.data_locks 를 찍는다.
 *  - footprint: 세션 하나가 패턴을 돌리며 커밋 직전까지 잡은 잠금(새 키일 때, 이미 있는 키일 때)
 *  - deadlock : 세션 여러 개가 문장을 정해진 순서로 보내며 교착 직전의 잠금을 찍는다
 * 키는 사람이 읽기 쉽게 고정 문자열을 쓴다. 시드 행 'k100' 'k200' 'k300' 사이에 'k150' 을 넣는다.
 */
public final class LockDump {

    static final String KEY = "k150";

    static void resetSmall() throws SQLException {
        try (Connection c = Bench.root(); Statement s = c.createStatement()) {
            s.execute("DROP TABLE IF EXISTS lab.visit");
            s.execute("""
                CREATE TABLE lab.visit (
                  id BIGINT AUTO_INCREMENT PRIMARY KEY,
                  user_key VARCHAR(32) NOT NULL,
                  payload VARCHAR(64) NOT NULL,
                  inserted_by VARCHAR(40) NOT NULL,
                  UNIQUE KEY uk_user_key (user_key)
                ) ENGINE=InnoDB""");
            s.execute("INSERT INTO lab.visit(user_key, payload, inserted_by) VALUES ('k100','seed','seed'),('k200','seed','seed'),('k300','seed','seed')");
        }
    }

    static long connId(Connection c) throws SQLException {
        try (Statement s = c.createStatement(); ResultSet rs = s.executeQuery("SELECT CONNECTION_ID()")) { rs.next(); return rs.getLong(1); }
    }

    // 잠금의 주인은 THREAD_ID 가 아니라 ENGINE_TRANSACTION_ID 로 가린다. 다른 세션이 암묵 잠금을 명시 잠금으로
    // 바꿔 줄 때 THREAD_ID 는 바꿔 준 세션 것으로 찍히기 때문이다(트랜잭션 id 는 원래 주인 것).
    static void dump(Connection root, Map<Long, String> names, String title) throws SQLException {
        System.out.println("  -- data_locks: " + title);
        String sql = """
            SELECT x.trx_mysql_thread_id, l.LOCK_TYPE, IFNULL(l.INDEX_NAME,'-'), l.LOCK_MODE, l.LOCK_STATUS, IFNULL(l.LOCK_DATA,'-')
            FROM performance_schema.data_locks l
            LEFT JOIN information_schema.innodb_trx x ON x.trx_id = l.ENGINE_TRANSACTION_ID
            WHERE l.OBJECT_NAME = 'visit'
            ORDER BY x.trx_mysql_thread_id, l.LOCK_TYPE DESC, l.INDEX_NAME, l.LOCK_DATA""";
        int n = 0;
        try (Statement s = root.createStatement(); ResultSet rs = s.executeQuery(sql)) {
            while (rs.next()) {
                n++;
                System.out.printf("     %-2s %-6s %-12s %-24s %-8s %s%n",
                        names.getOrDefault(rs.getLong(1), "?"), rs.getString(2), rs.getString(3), rs.getString(4), rs.getString(5), rs.getString(6));
            }
        }
        if (n == 0) System.out.println("     (no locks)");
    }

    // ---------------- footprint ----------------

    public static void footprint(String pattern, String iso) throws Exception {
        resetSmall();
        int level = iso.equals("RC") ? Connection.TRANSACTION_READ_COMMITTED : Connection.TRANSACTION_REPEATABLE_READ;
        String extra = pattern.equals("p2a") ? "&useAffectedRows=true" : "";
        System.out.printf("footprint pattern=%s iso=%s key=%s (seed rows k100 k200 k300)%n", pattern, iso, KEY);
        try (Connection root = Bench.root()) {
            for (String phase : new String[] {"new key", "existing key"}) {
                try (Connection c = Bench.open("lab", "lab", extra)) {
                    c.setAutoCommit(false);
                    c.setTransactionIsolation(level);
                    Map<Long, String> names = Map.of(connId(c), "S1");
                    System.out.println(" [" + phase + "]");
                    // 마지막 단계(커밋 직전)의 잠금만 찍는다. 커밋을 늦추려고 Step 에서 덤프한다.
                    List<String> labels = new ArrayList<>();
                    Patterns.Step step = label -> { labels.add(label); dump(root, names, label); };
                    Patterns.Verdict v = Patterns.run(pattern, c, KEY, "v1", phase.equals("new key") ? "S1-first" : "S1-second", step);
                    System.out.println("  verdict=" + v);
                }
            }
        }
    }

    // ---------------- stepped deadlock ----------------

    static final class Session implements AutoCloseable {
        final String name; final Connection c; final ExecutorService ex = Executors.newSingleThreadExecutor();
        Future<String> last;
        Session(String name, int level) throws SQLException {
            this.name = name;
            this.c = Bench.open("lab", "lab", "");
            c.setAutoCommit(false);
            c.setTransactionIsolation(level);
        }
        Future<String> send(String sql) {
            last = ex.submit(() -> {
                try (Statement s = c.createStatement()) {
                    if (sql.equals("COMMIT")) { c.commit(); return "ok"; }
                    if (s.execute(sql)) {
                        int rows = 0;
                        try (ResultSet rs = s.getResultSet()) { while (rs.next()) rows++; }
                        return "ok rows=" + rows;
                    }
                    return "ok affected=" + s.getUpdateCount();
                } catch (SQLException e) {
                    try { c.rollback(); } catch (SQLException ignore) {}
                    return "ERROR " + e.getErrorCode() + " " + e.getMessage();
                }
            });
            return last;
        }
        @Override public void close() throws Exception { ex.shutdownNow(); c.close(); }
    }

    static String state(Future<String> f) throws Exception {
        try { return f.get(400, TimeUnit.MILLISECONDS); } catch (TimeoutException e) { return "(waiting)"; }
    }

    static void step(Map<String, Session> ss, String who, String sql) throws Exception {
        Future<String> f = ss.get(who).send(sql);
        String st = state(f);
        System.out.printf("  %s> %s%n      => %s%n", who, sql, st);
    }

    static void settle(Map<String, Session> ss) throws Exception {
        for (Session s : ss.values()) {
            if (s.last != null && !s.last.isDone()) {
                String st = state(s.last);
                if (!st.equals("(waiting)")) System.out.printf("  %s   (earlier statement finished) => %s%n", s.name, st);
            }
        }
    }

    public static void deadlock(String pattern, String iso) throws Exception {
        resetSmall();
        int level = iso.equals("RC") ? Connection.TRANSACTION_READ_COMMITTED : Connection.TRANSACTION_REPEATABLE_READ;
        String ins = "INSERT INTO visit(user_key, payload, inserted_by) VALUES ('" + KEY + "','v1','%s')";
        String insIgnore = "INSERT IGNORE INTO visit(user_key, payload, inserted_by) VALUES ('" + KEY + "','v1','%s')";
        String forUpdate = "SELECT id FROM visit WHERE user_key='" + KEY + "' FOR UPDATE";
        System.out.printf("deadlock pattern=%s iso=%s key=%s (seed rows k100 k200 k300)%n", pattern, iso, KEY);
        Map<String, Session> ss = new LinkedHashMap<>();
        try (Connection root = Bench.root()) {
            for (String n : pattern.equals("p1") ? new String[] {"A", "B", "C"} : new String[] {"A", "B"}) ss.put(n, new Session(n, level));
            Map<Long, String> names = new LinkedHashMap<>();
            for (Session s : ss.values()) names.put(connId(s.c), s.name);
            if (pattern.equals("p1")) {
                step(ss, "A", insIgnore.formatted("A"));
                step(ss, "B", insIgnore.formatted("B"));
                step(ss, "C", insIgnore.formatted("C"));
                dump(root, names, "A inserted, B and C wait on the duplicate");
                step(ss, "A", forUpdate);
                step(ss, "A", "COMMIT");
                settle(ss);
                dump(root, names, "A committed, B and C got their duplicate locks");
                step(ss, "B", forUpdate);
                dump(root, names, "B asks for X on the row");
                step(ss, "C", forUpdate);
                settle(ss);
            } else {
                step(ss, "A", forUpdate);
                step(ss, "B", forUpdate);
                dump(root, names, "both locked a row that does not exist");
                step(ss, "A", ins.formatted("A"));
                dump(root, names, "A tries to insert");
                step(ss, "B", ins.formatted("B"));
                settle(ss);
                dump(root, names, "after B's insert");
                for (Session s : ss.values()) { if (s.last.isDone()) step(ss, s.name, "COMMIT"); }
                settle(ss);
            }
            try (Statement s = root.createStatement(); ResultSet rs = s.executeQuery("SELECT inserted_by FROM lab.visit WHERE user_key='" + KEY + "'")) {
                List<String> by = new ArrayList<>();
                while (rs.next()) by.add(rs.getString(1));
                System.out.println("  rows for key: " + by);
            }
        } finally {
            for (Session s : ss.values()) s.close();
        }
    }
}
