package lab.co4;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

class OrderHandler {
    private static final Logger log = LoggerFactory.getLogger(OrderHandler.class);
    private static final Logger auditTrail = LoggerFactory.getLogger("audit");
    static final boolean LEGACY_FORMAT = false;

    String handle(String id) {
        log.info("order received {}", id);                          // #S1 평범한 호출
        // log.info("old debug line {}", id);                       #G1 주석
        long total = Math.abs(id.hashCode()) % 1000;
        log
            .info("order total {}", total);                         // #S2 줄바꿈
        auditTrail.info("audit order {}", id);                      // #S9 변수 이름이 다름
        if (LEGACY_FORMAT) {
            log.info("legacy format {}", id);                       // #S3 죽은 분기
        }
        try {
            return place(id, total);
        } catch (IllegalStateException e) {
            log.info("order rejected {}", id, e);                   // #S4 예외 경로
            return "rejected";
        }
    }

    private String place(String id, long total) {
        if (id.startsWith("-")) throw new IllegalStateException("negative id");
        return "order " + id + " " + total;
    }
}
