package lab;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.Statement;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CyclicBarrier;
import java.util.concurrent.TimeUnit;

import org.junit.jupiter.api.Test;

/**
 * H2 MySQL 모드에서 1편의 교착 조건을 세 세션으로 만든다.
 * A 가 넣고(미커밋), B 와 C 가 같은 키로 INSERT IGNORE 를 보내 함께 기다린다.
 * A 가 커밋한 뒤 B 와 C 가 둘 다 INSERT IGNORE 를 끝낸 것을 배리어로 맞추고, 그다음에 둘 다 FOR UPDATE 를 보낸다.
 * InnoDB 라면 이 지점에서 B 와 C 가 각자 쥔 S 잠금 때문에 서로 막혀 1213 이 난다(1편).
 * 단언은 없다. 시각과 결과를 찍는 관찰용이다.
 */
class H2LockProbeTest {

    static final String URL = "jdbc:h2:mem:probe;MODE=MySQL;DATABASE_TO_LOWER=TRUE;DB_CLOSE_DELAY=-1;LOCK_TIMEOUT=10000";

    @Test
    void probe() throws Exception {
        try (Connection c0 = DriverManager.getConnection(URL, "sa", ""); Statement s = c0.createStatement()) {
            s.execute("DROP TABLE IF EXISTS first_visit");
            s.execute("CREATE TABLE first_visit (user_id BIGINT NOT NULL PRIMARY KEY, cnt INT NOT NULL)");
        }
        long t0 = System.nanoTime();
        CyclicBarrier bothInserted = new CyclicBarrier(2);
        try (Connection a = DriverManager.getConnection(URL, "sa", "");
             Connection b = DriverManager.getConnection(URL, "sa", "");
             Connection c = DriverManager.getConnection(URL, "sa", "")) {
            a.setAutoCommit(false);
            b.setAutoCommit(false);
            c.setAutoCommit(false);
            log(t0, "A INSERT IGNORE -> " + insertIgnore(a));
            CompletableFuture<Void> fb = waiter(t0, "B", b, bothInserted);
            CompletableFuture<Void> fc = waiter(t0, "C", c, bothInserted);
            Thread.sleep(1000);
            log(t0, "A SELECT ... FOR UPDATE, UPDATE, COMMIT");
            forUpdateAndIncrement(a);
            a.commit();
            fb.get(30, TimeUnit.SECONDS);
            fc.get(30, TimeUnit.SECONDS);
        }
        try (Connection c0 = DriverManager.getConnection(URL, "sa", "");
             Statement s = c0.createStatement();
             java.sql.ResultSet rs = s.executeQuery("SELECT cnt FROM first_visit WHERE user_id = 1")) {
            rs.next();
            log(t0, "최종 cnt = " + rs.getInt(1));
        }
    }

    static CompletableFuture<Void> waiter(long t0, String name, Connection conn, CyclicBarrier bothInserted) {
        return CompletableFuture.runAsync(() -> {
            try {
                log(t0, name + " INSERT IGNORE 시작");
                log(t0, name + " INSERT IGNORE -> " + insertIgnore(conn));
                bothInserted.await(10, TimeUnit.SECONDS);   // B, C 둘 다 중복 검사를 마친 뒤에
                log(t0, name + " SELECT ... FOR UPDATE 시작");
                forUpdateAndIncrement(conn);
                log(t0, name + " SELECT ... FOR UPDATE, UPDATE 끝");
                conn.commit();
                log(t0, name + " COMMIT");
            } catch (Exception e) {
                log(t0, name + " 예외 " + e);
            }
        });
    }

    static int insertIgnore(Connection c) throws Exception {
        try (PreparedStatement ps = c.prepareStatement("INSERT IGNORE INTO first_visit (user_id, cnt) VALUES (1, 0)")) {
            return ps.executeUpdate();
        }
    }

    static void forUpdateAndIncrement(Connection c) throws Exception {
        try (PreparedStatement ps = c.prepareStatement("SELECT cnt FROM first_visit WHERE user_id = 1 FOR UPDATE")) {
            ps.executeQuery().close();
        }
        try (PreparedStatement ps = c.prepareStatement("UPDATE first_visit SET cnt = cnt + 1 WHERE user_id = 1")) {
            ps.executeUpdate();
        }
    }

    static synchronized void log(long t0, String m) {
        System.out.printf("  +%4dms %s%n", (System.nanoTime() - t0) / 1_000_000, m);
    }
}
