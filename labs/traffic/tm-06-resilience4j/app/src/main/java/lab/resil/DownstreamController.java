package lab.resil;

import java.util.Map;
import java.util.concurrent.ThreadLocalRandom;

import org.springframework.context.annotation.Profile;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 하위 서비스. /recommend 는 지연과 실패율을 실행 중에 바꿀 수 있고, /pay 는 늘 5ms 로 성공한다.
 * 장애 주입: curl -X POST 'localhost:28082/admin/fault?delayMs=1000&errorRate=0'
 */
@RestController
@Profile("downstream")
public class DownstreamController {

    private volatile long delayMs = Long.getLong("lab.delayMs", 50);
    private volatile double errorRate = 0;

    @GetMapping("/recommend")
    public ResponseEntity<String> recommend() throws InterruptedException {
        long d = delayMs;
        if (d > 0) Thread.sleep(d);
        if (ThreadLocalRandom.current().nextDouble() < errorRate) {
            return ResponseEntity.status(500).body("boom");
        }
        return ResponseEntity.ok("[\"item-1\",\"item-2\"]");
    }

    @GetMapping("/pay")
    public String pay() throws InterruptedException {
        Thread.sleep(5);
        return "paid";
    }

    @PostMapping("/admin/fault")
    public Map<String, Object> fault(@RequestParam(defaultValue = "50") long delayMs,
                                     @RequestParam(defaultValue = "0") double errorRate) {
        this.delayMs = delayMs;
        this.errorRate = errorRate;
        return Map.of("delayMs", delayMs, "errorRate", errorRate);
    }
}
