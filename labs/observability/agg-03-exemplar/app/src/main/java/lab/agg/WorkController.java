package lab.agg;

import java.util.Map;
import java.util.concurrent.ThreadLocalRandom;

import io.micrometer.observation.Observation;
import io.micrometer.observation.ObservationRegistry;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 지연 분포를 환경변수로 정하는 엔드포인트.
 * 보통 요청은 20~60ms, slow-ratio 비율은 300~500ms, very-slow-ratio 비율은 1~2초 걸린다.
 * 느린 구간을 lab.work 라는 Observation 으로 감싸서 트레이스에 자식 스팬과 slow 태그가 남게 했다.
 */
@RestController
public class WorkController {

    private final ObservationRegistry observations;
    private final double slowRatio, verySlowRatio;

    public WorkController(ObservationRegistry observations,
                          @Value("${lab.slow-ratio:0.1}") double slowRatio,
                          @Value("${lab.very-slow-ratio:0.01}") double verySlowRatio) {
        this.observations = observations;
        this.slowRatio = slowRatio;
        this.verySlowRatio = verySlowRatio;
    }

    @GetMapping("/work")
    public Map<String, Object> work() {
        ThreadLocalRandom r = ThreadLocalRandom.current();
        double x = r.nextDouble();
        String kind = x < verySlowRatio ? "very_slow" : x < verySlowRatio + slowRatio ? "slow" : "fast";
        long ms = switch (kind) {
            case "very_slow" -> r.nextLong(1000, 2000);
            case "slow" -> r.nextLong(300, 500);
            default -> r.nextLong(20, 60);
        };
        Observation.createNotStarted("lab.work", observations)
                .lowCardinalityKeyValue("kind", kind)
                .observe(() -> sleep(ms));
        return Map.of("slept_ms", ms, "kind", kind);
    }

    private static void sleep(long ms) {
        try {
            Thread.sleep(ms);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}
