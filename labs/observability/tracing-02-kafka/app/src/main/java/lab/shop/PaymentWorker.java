package lab.shop;

import java.util.concurrent.BlockingQueue;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.LinkedBlockingQueue;

import io.opentelemetry.context.Context;
import io.opentelemetry.context.Scope;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Profile;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

/**
 * 결제 처리. 컨슈머 스레드에서 바로 하거나(inline), 다른 스레드로 넘긴다.
 *   executor  : Executors.newFixedThreadPool 에 submit
 *   queue     : 직접 만든 작업 큐 + 워커 스레드 (메시지만 넘긴다)
 *   queue-ctx : 같은 큐에 OTel Context 를 같이 넣어 워커에서 복원한다
 */
@Profile("payment")
@Component
class PaymentWorker {

    private static final Logger log = LoggerFactory.getLogger(PaymentWorker.class);

    record Job(String payload, Context ctx) {}

    private final JdbcTemplate jdbc;
    private final String handoff;
    private final ExecutorService pool = Executors.newFixedThreadPool(4);
    private final BlockingQueue<Job> queue = new LinkedBlockingQueue<>();

    PaymentWorker(JdbcTemplate jdbc, @Value("${shop.payment.handoff}") String handoff) {
        this.jdbc = jdbc;
        this.handoff = handoff;
        for (int i = 0; i < 4; i++) {
            Thread t = new Thread(this::drain, "pay-worker-" + i);
            t.setDaemon(true);
            t.start();
        }
        log.info("handoff={}", handoff);
    }

    void accept(String payload) {
        log.info("주문 수신 {}", payload);
        switch (handoff) {
            case "executor" -> pool.submit(() -> pay(payload));
            case "queue" -> queue.add(new Job(payload, null));
            case "queue-ctx" -> queue.add(new Job(payload, Context.current()));   // 캡처
            default -> pay(payload);
        }
    }

    private void drain() {
        while (true) {
            try {
                Job job = queue.take();
                if (job.ctx() == null) {
                    pay(job.payload());
                } else {
                    try (Scope ignored = job.ctx().makeCurrent()) {   // 복원, 끝나면 되돌림
                        pay(job.payload());
                    }
                }
            } catch (InterruptedException e) {
                return;
            }
        }
    }

    private void pay(String payload) {
        String[] f = payload.split(",");
        jdbc.update("insert into payments values (?, ?, ?, current_timestamp)", f[0], f[1], Integer.parseInt(f[2]));
        log.info("결제 완료 order={}", f[0]);
    }
}
