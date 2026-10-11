package lab.traffic;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import jakarta.servlet.http.HttpServletRequest;
import java.net.http.HttpClient;
import java.time.Duration;
import java.util.concurrent.ThreadLocalRandom;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestClient;

/**
 * 지연과 실패를 환경변수로 조절하는 작은 백엔드.
 * BASE_MS + [0, JITTER_MS) 만큼 자고, SLOW_RATIO 확률로 SLOW_MS 를 더 잔다. FAIL_RATE 확률로 503.
 * DOWNSTREAM_URL 이 있으면 자기 일을 한 뒤 그 주소를 부르고, 받은 상태 코드를 그대로 돌려준다(실습-5).
 */
@RestController
public class WorkController {
    private static final Logger log = LoggerFactory.getLogger(WorkController.class);

    @Value("${BASE_MS:5}") long baseMs;
    @Value("${JITTER_MS:0}") long jitterMs;
    @Value("${SLOW_RATIO:0}") double slowRatio;
    @Value("${SLOW_MS:300}") long slowMs;
    @Value("${FAIL_RATE:0}") double failRate;
    @Value("${LOG_ARRIVALS:false}") boolean logArrivals;
    @Value("${SERVICE_NAME:backend}") String service;

    private final RestClient downstream;
    private final Counter received;

    public WorkController(@Value("${DOWNSTREAM_URL:}") String downstreamUrl, MeterRegistry registry) {
        var http = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(1)).build();
        var factory = new JdkClientHttpRequestFactory(http);
        factory.setReadTimeout(Duration.ofSeconds(10));
        this.downstream = downstreamUrl.isBlank() ? null
                : RestClient.builder().baseUrl(downstreamUrl).requestFactory(factory).build();
        this.received = Counter.builder("lab.work.received").register(registry);
    }

    @RequestMapping("/work")
    public ResponseEntity<String> work(HttpServletRequest req, @RequestBody(required = false) byte[] body)
            throws InterruptedException {
        received.increment();
        var rnd = ThreadLocalRandom.current();
        if (logArrivals) {
            // 같은 요청의 원본과 사본은 x-request-id 가 같다. 도착 시각으로 사본이 얼마 뒤에 왔는지 잰다.
            log.info("arrival rid={} attempt={} method={} clen={} body={} t_us={}",
                    req.getHeader("x-request-id"), req.getHeader("x-envoy-attempt-count"),
                    req.getMethod(), req.getHeader("content-length"), body == null ? 0 : body.length,
                    java.time.temporal.ChronoUnit.MICROS.between(java.time.Instant.EPOCH, java.time.Instant.now()));
        }
        long sleep = baseMs + (jitterMs > 0 ? rnd.nextLong(jitterMs) : 0);
        boolean slow = rnd.nextDouble() < slowRatio;
        if (slow) sleep += slowMs;
        Thread.sleep(sleep);
        if (rnd.nextDouble() < failRate) {
            return ResponseEntity.status(503).body(service + " failed\n");
        }
        if (downstream != null) {
            var res = downstream.get().uri("/work")
                    .exchange((rq, rs) -> ResponseEntity.status(rs.getStatusCode()).body(service + " <- " + rs.getStatusCode().value() + "\n"));
            return res;
        }
        return ResponseEntity.ok(service + " ok slept=" + sleep + "ms body=" + (body == null ? 0 : body.length) + "\n");
    }
}
