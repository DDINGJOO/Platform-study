package lab.upsert;

import java.util.List;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.atomic.AtomicInteger;

import org.springframework.dao.PessimisticLockingFailureException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.resilience.annotation.Retryable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

/**
 * 같은 메서드에 @Retryable 과 @Transactional 을 함께 붙였을 때, 재시도가 트랜잭션 바깥에서 도는지 본다.
 * 패턴 ① 을 JdbcTemplate 으로 짠다. 교착이면 Spring 이 어떤 예외로 바꾸는지도 여기서 본다.
 */
@Service
public class VisitService {

    private final JdbcTemplate jdbc;
    /** 시도마다 (트랜잭션 id, 끝난 상태)를 남긴다. order 모드가 읽는다. */
    private final ConcurrentLinkedQueue<String> trace = new ConcurrentLinkedQueue<>();
    private final AtomicInteger attempts = new AtomicInteger();

    // 프록시(CGLIB)의 필드는 비어 있으므로 메서드로 읽는다.
    public List<String> trace() { return List.copyOf(trace); }
    public int attempts() { return attempts.get(); }

    public VisitService(JdbcTemplate jdbc) { this.jdbc = jdbc; }

    @Transactional(isolation = Isolation.REPEATABLE_READ)
    public Patterns.Verdict p1Plain(String key, String reqId) { return p1(key, reqId); }

    @Retryable(includes = PessimisticLockingFailureException.class, maxRetries = 3, delay = 20, jitter = 10)
    @Transactional(isolation = Isolation.REPEATABLE_READ)
    public Patterns.Verdict p1WithRetry(String key, String reqId) { return p1(key, reqId); }

    private Patterns.Verdict p1(String key, String reqId) {
        attempts.incrementAndGet();
        int n = jdbc.update("INSERT IGNORE INTO visit(user_key, payload, inserted_by) VALUES (?,?,?)", key, "v1", reqId);
        jdbc.queryForList("SELECT id FROM visit WHERE user_key=? FOR UPDATE", key);
        return n == 1 ? Patterns.Verdict.SAVED : Patterns.Verdict.DUPLICATE;
    }

    /** 첫 시도에서만 실패하는 메서드. 시도마다 트랜잭션이 새로 열렸다가 닫히는지 기록한다. */
    @Retryable(includes = PessimisticLockingFailureException.class, maxRetries = 3, delay = 20)
    @Transactional
    public String failOnce(String key) {
        int attempt = attempts.incrementAndGet();
        jdbc.update("INSERT INTO visit(user_key, payload, inserted_by) VALUES (?,?,?)", key + "-" + attempt, "v1", "order");
        Long conn = jdbc.queryForObject("SELECT CONNECTION_ID()", Long.class);
        boolean active = TransactionSynchronizationManager.isActualTransactionActive();
        trace.add("attempt " + attempt + " start: tx_active=" + active + " connection_id=" + conn + " inserted " + key + "-" + attempt);
        TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
            @Override public void afterCompletion(int status) {
                trace.add("attempt " + attempt + " tx completed: " + (status == STATUS_COMMITTED ? "COMMITTED" : status == STATUS_ROLLED_BACK ? "ROLLED_BACK" : "UNKNOWN"));
            }
        });
        if (attempt == 1) throw new org.springframework.dao.CannotAcquireLockException("synthetic deadlock on attempt 1");
        return "ok on attempt " + attempt;
    }
}
