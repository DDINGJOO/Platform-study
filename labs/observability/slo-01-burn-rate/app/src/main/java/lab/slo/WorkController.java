package lab.slo;

import java.util.Map;
import java.util.concurrent.ThreadLocalRandom;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/** 부하 대상 엔드포인트. 실패율과 지연은 ChaosController 가 실행 중에 바꾼다. */
@RestController
public class WorkController {

    private final Chaos chaos;

    public WorkController(Chaos chaos) {
        this.chaos = chaos;
    }

    @GetMapping("/api/work")
    public ResponseEntity<Map<String, Object>> work() throws InterruptedException {
        ThreadLocalRandom r = ThreadLocalRandom.current();
        Thread.sleep(5 + r.nextLong(10) + chaos.latencyMs);
        // 요청마다 작은 객체를 조금 만든다(평소 할당량)
        byte[] payload = new byte[16 * 1024];
        if (r.nextDouble() < chaos.errorRate) {
            return ResponseEntity.status(500).body(Map.of("result", "error"));
        }
        return ResponseEntity.ok(Map.of("result", "ok", "size", payload.length));
    }
}
