package lab.agg;

import java.util.Map;
import java.util.concurrent.ThreadLocalRandom;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 주문 엔드포인트. 실패율을 실행 중에 바꿀 수 있다.
 *  - client-error-rate 비율은 400(잘못된 요청)으로 돌려준다. 서버 잘못이 아니다
 *  - fail-rate 비율은 500으로 돌려준다. 서버 잘못이다
 * POST /admin/fail-rate?value=0.3 으로 500 비율을 바꾼다.
 */
@RestController
public class OrderController {

    private final double clientErrorRate;
    private volatile double failRate;

    public OrderController(@Value("${lab.client-error-rate:0.03}") double clientErrorRate,
                           @Value("${lab.fail-rate:0}") double failRate) {
        this.clientErrorRate = clientErrorRate;
        this.failRate = failRate;
    }

    @PostMapping("/orders")
    public ResponseEntity<Map<String, Object>> order() throws InterruptedException {
        ThreadLocalRandom r = ThreadLocalRandom.current();
        Thread.sleep(5 + r.nextLong(15));
        double x = r.nextDouble();
        if (x < clientErrorRate) {
            return ResponseEntity.badRequest().body(Map.of("result", "bad_request"));
        }
        if (x < clientErrorRate + failRate) {
            return ResponseEntity.status(500).body(Map.of("result", "error"));
        }
        return ResponseEntity.ok(Map.of("result", "ok"));
    }

    @PostMapping("/admin/fail-rate")
    public Map<String, Object> setFailRate(@RequestParam double value) {
        this.failRate = value;
        return Map.of("fail_rate", value);
    }
}
