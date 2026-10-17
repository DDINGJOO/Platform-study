package lab.rollback;

import java.sql.Connection;
import java.sql.SQLException;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

import javax.sql.DataSource;

import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.core.SpringVersion;
import org.springframework.dao.CannotAcquireLockException;
import org.springframework.dao.PessimisticLockingFailureException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * 모드
 *   versions
 *   throw  <jdbc|repo|commit|em> <1213|1205>   예외를 트랜잭션 밖으로 그대로 던지게 두고, 받은 타입을 찍는다
 *   catch  <jdbc|repo> <1213|1205>             트랜잭션 안에서 잡고 계속 진행한 뒤 커밋한다. 무엇이 남는지 본다
 *
 * kind
 *   jdbc   : JdbcTemplate.update
 *   repo   : Spring Data 저장소 findById → 값 변경 → saveAndFlush
 *   commit : 첫 잠금은 saveAndFlush, 마지막 변경은 flush 하지 않고 커밋 때 나가게 한다
 *   em     : @Repository 가 아닌 빈에서 EntityManager.find → 변경 → flush
 */
@SpringBootApplication
public class ScopeApplication implements CommandLineRunner {

    public static void main(String[] args) {
        System.exit(SpringApplication.exit(SpringApplication.run(ScopeApplication.class, args)));
    }

    final JdbcTemplate jdbc;
    final TransactionTemplate tx;
    final ItemRepository items;
    final NoteRepository notes;
    final EmWork emWork;
    final DataSource ds;

    ScopeApplication(JdbcTemplate jdbc, PlatformTransactionManager tm, ItemRepository items,
                     NoteRepository notes, EmWork emWork, DataSource ds) {
        this.jdbc = jdbc;
        this.tx = new TransactionTemplate(tm);
        this.items = items;
        this.notes = notes;
        this.emWork = emWork;
        this.ds = ds;
    }

    @Override
    public void run(String... args) throws Exception {
        String[] a = java.util.Arrays.stream(args).filter(s -> !s.startsWith("--")).toArray(String[]::new);
        switch (a[0]) {
            case "versions" -> versions();
            case "throw" -> scenario(a[1], a[2], false);
            case "catch" -> scenario(a[1], a[2], true);
            default -> throw new IllegalArgumentException(a[0]);
        }
    }

    void versions() throws SQLException {
        try (Connection c = ds.getConnection()) {
            var md = c.getMetaData();
            System.out.println("MySQL server       : " + md.getDatabaseProductVersion());
            System.out.println("Connector/J        : " + md.getDriverVersion());
        }
        System.out.println("Spring Framework   : " + SpringVersion.getVersion());
        System.out.println("Hibernate ORM      : " + org.hibernate.Version.getVersionString());
        System.out.println("Java               : " + System.getProperty("java.version"));
        System.out.println("JdbcTemplate translator : " + jdbc.getExceptionTranslator().getClass().getName());
        for (String n : List.of("org.springframework.dao.DeadlockLoserDataAccessException",
                "org.springframework.dao.CannotSerializeTransactionException",
                "org.springframework.dao.CannotAcquireLockException")) {
            try {
                Class<?> k = Class.forName(n);
                Deprecated d = k.getAnnotation(Deprecated.class);
                System.out.println(k.getSimpleName() + " : " + (d == null ? "not deprecated" : "@Deprecated(since=\"" + d.since() + "\")")
                        + "  parent=" + k.getSuperclass().getSimpleName());
            } catch (ClassNotFoundException e) {
                System.out.println(n + " : (class not found)");
            }
        }
    }

    // ---- 행 하나를 잠그는 일(UPDATE) ----
    void touch(String kind, int id, boolean deferFlush) {
        switch (kind) {
            case "jdbc" -> jdbc.update("UPDATE item SET v = v + 1 WHERE id = ?", id);
            case "repo" -> { Item it = items.findById(id).orElseThrow(); it.v++; items.saveAndFlush(it); }
            case "commit" -> {
                Item it = items.findById(id).orElseThrow(); it.v++;
                if (!deferFlush) items.saveAndFlush(it);   // deferFlush 면 커밋 때 UPDATE 가 나간다
            }
            case "em" -> emWork.touch(id);
            default -> throw new IllegalArgumentException(kind);
        }
    }

    // ---- 잠금 앞에 남기는 기록(INSERT) ----
    void note(String kind, String who) {
        switch (kind) {
            case "jdbc" -> jdbc.update("INSERT INTO note(who) VALUES (?)", who);
            case "em" -> emWork.note(who);
            default -> notes.saveAndFlush(new Note(who));
        }
    }

    void scenario(String kind, String code, boolean catchInside) throws Exception {
        jdbc.update("DELETE FROM note");
        jdbc.update("UPDATE item SET v = 0");
        System.out.println("== " + (catchInside ? "catch" : "throw") + " kind=" + kind + " code=" + code);
        ExecutorService pool = Executors.newFixedThreadPool(2);
        CountDownLatch aLocked = new CountDownLatch(1);
        CountDownLatch bLocked = new CountDownLatch(1);
        long t0 = System.nanoTime();

        Future<String> fa;
        Future<String> fb;
        if (code.equals("1213")) {
            // A: 기록 3건(더 무거운 쪽) → item 1 잠금 → B 를 기다렸다가 item 2
            fa = pool.submit(() -> outcome("A", () -> tx.executeWithoutResult(s -> {
                for (int i = 0; i < 3; i++) note(kind, "A-before");
                touch(kind, 1, false);
                aLocked.countDown();
                await(bLocked);
                touch(kind, 2, true);
            })));
            // B: 기록 1건 → item 2 잠금 → item 1 (여기서 순환이 닫힌다)
            fb = pool.submit(() -> outcome("B", () -> tx.executeWithoutResult(s -> {
                await(aLocked);
                note(kind, "B-before");
                touch(kind, 2, false);
                bLocked.countDown();
                sleep(300);
                lockStep(kind, 1, catchInside);
                if (catchInside) note(kind, "B-after");
            })));
        } else {
            // A: item 1 을 잡고 4초 쥐고 있다가 롤백 (B 의 기다림 2초보다 길다)
            fa = pool.submit(() -> outcome("A(holder)", () -> tx.executeWithoutResult(s -> {
                jdbc.update("UPDATE item SET v = v + 100 WHERE id = 1");
                aLocked.countDown();
                sleep(4000);
                s.setRollbackOnly();
            })));
            fb = pool.submit(() -> outcome("B", () -> tx.executeWithoutResult(s -> {
                await(aLocked);
                note(kind, "B-before");
                lockStep(kind, 1, catchInside);
                if (catchInside) note(kind, "B-after");
            })));
        }
        String ra = fa.get(30, TimeUnit.SECONDS);
        String rb = fb.get(30, TimeUnit.SECONDS);
        pool.shutdown();
        System.out.println(ra);
        System.out.println(rb);
        System.out.printf("elapsed %.1fs%n", (System.nanoTime() - t0) / 1e9);
        System.out.println("note rows after : " + jdbc.queryForList("SELECT who FROM note ORDER BY id", String.class));
        System.out.println("item v after    : " + jdbc.queryForList("SELECT CONCAT(id, '=', v) FROM item ORDER BY id", String.class));
    }

    /** 잠금 문장. catchInside 면 여기서 잡고 트랜잭션을 계속 진행한다. */
    void lockStep(String kind, int id, boolean catchInside) {
        if (!catchInside) { touch(kind, id, true); return; }
        try {
            touch(kind, id, false);
            System.out.println("  B lock statement: ok");
        } catch (RuntimeException e) {
            System.out.println("  B caught INSIDE the transaction, continuing:");
            System.out.print(describe("    ", e));
        }
    }

    String outcome(String who, Runnable r) {
        try {
            r.run();
            return "  " + who + " : no exception" + (who.startsWith("A(holder)") ? " (rolled back on purpose by setRollbackOnly)" : " (committed)");
        } catch (RuntimeException e) {
            return "  " + who + " : exception out of TransactionTemplate\n" + describe("    ", e);
        }
    }

    static String describe(String ind, Throwable e) {
        StringBuilder sb = new StringBuilder();
        sb.append(ind).append("type   : ").append(e.getClass().getName()).append('\n');
        if (!(e instanceof org.springframework.dao.DataAccessException) && e.getMessage() != null) {
            String m = e.getMessage().lines().findFirst().orElse("");
            sb.append(ind).append("message: ").append(m.length() > 110 ? m.substring(0, 110) + "..." : m).append('\n');
        }
        StringBuilder parents = new StringBuilder();
        for (Class<?> k = e.getClass().getSuperclass(); k != null && k != Object.class; k = k.getSuperclass()) {
            if (k == RuntimeException.class) break;
            parents.append(parents.isEmpty() ? "" : " > ").append(k.getSimpleName());
        }
        sb.append(ind).append("parents: ").append(parents).append('\n');
        for (Throwable t = e.getCause(); t != null; t = t.getCause()) {
            sb.append(ind).append("cause  : ").append(t.getClass().getName());
            if (t instanceof SQLException s) {
                sb.append("  [SQLState=").append(s.getSQLState()).append(", errorCode=").append(s.getErrorCode()).append("]");
            }
            sb.append('\n');
        }
        sb.append(ind).append("is PessimisticLockingFailureException=").append(e instanceof PessimisticLockingFailureException)
          .append("  CannotAcquireLockException=").append(e instanceof CannotAcquireLockException)
          .append("  DeadlockLoserDataAccessException=").append(isDeadlockLoser(e)).append('\n');
        return sb.toString();
    }

    @SuppressWarnings("deprecation")
    static boolean isDeadlockLoser(Throwable e) {
        return e instanceof org.springframework.dao.DeadlockLoserDataAccessException;
    }

    static void await(CountDownLatch l) {
        try { if (!l.await(20, TimeUnit.SECONDS)) throw new IllegalStateException("latch timeout"); }
        catch (InterruptedException e) { throw new IllegalStateException(e); }
    }

    static void sleep(long ms) {
        try { Thread.sleep(ms); } catch (InterruptedException e) { throw new IllegalStateException(e); }
    }
}
