package lab.agg;

import java.util.Map;
import java.util.concurrent.ThreadLocalRandom;

import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 지연 분포를 환경변수로 정하는 엔드포인트.
 * 보통 요청은 fast-min ~ fast-max ms, slow-ratio 비율의 요청은 slow-min ~ slow-max ms 동안 잔다.
 *
 * 같은 요청을 두 미터가 잰다.
 *  - http.server.requests : 스프링이 자동으로 거는 타이머. application.yml 에서 버킷(히스토그램)을 켰다
 *  - lab.work             : 여기서 직접 거는 타이머. application.yml 에서 클라이언트 p99 만 켰다
 * Micrometer 1.13 이후 Prometheus 레지스트리는 버킷을 켠 타이머의 클라이언트 백분위를 내보내지 않아서 둘로 나눴다.
 */
@RestController
public class WorkController {

    private final Timer workTimer;
    private final double slowRatio;
    private final long fastMin, fastMax, slowMin, slowMax;

    public WorkController(MeterRegistry registry,
                          @Value("${lab.slow-ratio:0}") double slowRatio,
                          @Value("${lab.fast-min-ms:20}") long fastMin,
                          @Value("${lab.fast-max-ms:60}") long fastMax,
                          @Value("${lab.slow-min-ms:300}") long slowMin,
                          @Value("${lab.slow-max-ms:500}") long slowMax) {
        this.workTimer = Timer.builder("lab.work").register(registry);
        this.slowRatio = slowRatio;
        this.fastMin = fastMin;
        this.fastMax = fastMax;
        this.slowMin = slowMin;
        this.slowMax = slowMax;
    }

    @GetMapping("/work")
    public Map<String, Object> work() throws InterruptedException {
        ThreadLocalRandom r = ThreadLocalRandom.current();
        boolean slow = r.nextDouble() < slowRatio;
        long ms = slow ? r.nextLong(slowMin, slowMax) : r.nextLong(fastMin, fastMax);
        Timer.Sample sample = Timer.start();
        Thread.sleep(ms);
        sample.stop(workTimer);
        return Map.of("slept_ms", ms, "slow", slow);
    }
}
