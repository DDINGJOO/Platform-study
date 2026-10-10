package lab.shop;

import java.util.Map;
import java.util.concurrent.ThreadLocalRandom;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Profile;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@Profile("payment")
@RestController
public class PaymentController {

    private static final Logger log = LoggerFactory.getLogger(PaymentController.class);
    private final double failRate;
    private final long slowMs;

    public PaymentController(@Value("${shop.payment.fail-rate:0}") double failRate,
                             @Value("${shop.payment.slow-ms:0}") long slowMs) {
        this.failRate = failRate;
        this.slowMs = slowMs;
    }

    @PostMapping("/payments")
    public ResponseEntity<Map<String, Object>> pay(@RequestBody Map<String, Object> body) throws InterruptedException {
        ThreadLocalRandom r = ThreadLocalRandom.current();
        Thread.sleep(20 + r.nextLong(30) + slowMs);
        if (r.nextDouble() < failRate) {
            log.error("PG 승인 거절 sku={} code=PG_TIMEOUT", body.get("sku"));
            return ResponseEntity.status(500).body(Map.of("result", "pg_error"));
        }
        return ResponseEntity.ok(Map.of("result", "paid"));
    }
}
