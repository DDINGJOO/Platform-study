package lab.traffic;

import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Semaphore;
import java.util.concurrent.ThreadLocalRandom;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import io.micrometer.core.instrument.DistributionSummary;
import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 트래픽 실습용 백엔드. GET /work 하나가 아래 손잡이대로 움직인다.
 *
 *  delay-ms        요청마다 잠드는 시간(ms). jitter-ms 만큼 무작위로 더한다
 *  max-concurrent  동시에 처리하는 요청 수 한도(0 = 무제한). 넘친 요청은 앱 안에서 줄을 선다
 *  fail            true 면 아무 일도 안 하고 즉시 503 을 돌려준다(빨리 실패하는 서버)
 *  cpu-rounds      CPU 일(JSON 비슷한 문자열 만들기, 정규식, 정렬, SHA-256)을 몇 번 돌지. JIT 워밍업을 보려고 둔다
 *
 * 값은 환경변수(LAB_DELAY_MS 등)로 시작하고, POST /chaos 로 실행 중에 바꾼다(재시작하면 워밍업 상태가 바뀌니까).
 * 응답 헤더 X-Instance 에 인스턴스 이름을 실어 Envoy 접근 로그가 어느 서버로 갔는지 남기게 한다.
 */
@RestController
public class WorkController {

    private final String instance;
    private volatile long delayMs;
    private volatile long jitterMs;
    private volatile boolean fail;
    private volatile int cpuRounds;
    private volatile int maxConcurrent;
    private volatile Semaphore permits;

    private final AtomicInteger inflight = new AtomicInteger();
    private final DistributionSummary inflightAtArrival;

    public WorkController(MeterRegistry registry,
                          @Value("${LAB_INSTANCE:unknown}") String instance,
                          @Value("${LAB_DELAY_MS:10}") long delayMs,
                          @Value("${LAB_JITTER_MS:0}") long jitterMs,
                          @Value("${LAB_FAIL:false}") boolean fail,
                          @Value("${LAB_CPU_ROUNDS:0}") int cpuRounds,
                          @Value("${LAB_MAX_CONCURRENT:0}") int maxConcurrent) {
        this.instance = instance;
        this.delayMs = delayMs;
        this.jitterMs = jitterMs;
        this.fail = fail;
        this.cpuRounds = cpuRounds;
        setMaxConcurrent(maxConcurrent);
        // 요청이 도착한 순간 이 인스턴스가 이미 처리 중이던 요청 수. 몰림(herd)을 인스턴스 쪽에서 본다
        this.inflightAtArrival = DistributionSummary.builder("lab.inflight.at.arrival")
                .serviceLevelObjectives(0.5, 1.5, 2.5, 3.5, 4.5, 6.5, 8.5, 10.5, 15.5, 20.5, 30.5, 50.5) // 값이 정수라 경계를 .5 에 둔다. le=0.5 는 '0개'
                .register(registry);
        Gauge.builder("lab.inflight", inflight, AtomicInteger::get).register(registry);
        Gauge.builder("lab.fail", this, c -> c.fail ? 1 : 0).register(registry);
    }

    private void setMaxConcurrent(int n) {
        this.maxConcurrent = n;
        this.permits = n > 0 ? new Semaphore(n, true) : null;
    }

    @GetMapping("/work")
    public ResponseEntity<Map<String, Object>> work() throws Exception {
        inflightAtArrival.record(inflight.getAndIncrement());
        try {
            if (fail) {
                return ResponseEntity.status(503).header("X-Instance", instance)
                        .body(Map.of("instance", instance, "error", "dependency down"));
            }
            Semaphore p = permits;
            if (p != null) p.acquire();
            try {
                long ms = delayMs + (jitterMs > 0 ? ThreadLocalRandom.current().nextLong(jitterMs + 1) : 0);
                if (ms > 0) Thread.sleep(ms);
                String digest = cpuRounds > 0 ? cpuWork(cpuRounds) : "";
                return ResponseEntity.ok().header("X-Instance", instance)
                        .body(Map.of("instance", instance, "slept_ms", ms, "digest", digest));
            } finally {
                if (p != null) p.release();
            }
        } finally {
            inflight.decrementAndGet();
        }
    }

    /** 실행 중에 손잡이를 바꾼다. 준 값만 바뀐다 */
    @PostMapping("/chaos")
    public Map<String, Object> chaos(@RequestParam(required = false) Long delayMs,
                                     @RequestParam(required = false) Long jitterMs,
                                     @RequestParam(required = false) Boolean fail,
                                     @RequestParam(required = false) Integer cpuRounds,
                                     @RequestParam(required = false) Integer maxConcurrent) {
        if (delayMs != null) this.delayMs = delayMs;
        if (jitterMs != null) this.jitterMs = jitterMs;
        if (fail != null) this.fail = fail;
        if (cpuRounds != null) this.cpuRounds = cpuRounds;
        if (maxConcurrent != null) setMaxConcurrent(maxConcurrent);
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("instance", instance);
        m.put("delayMs", this.delayMs);
        m.put("jitterMs", this.jitterMs);
        m.put("fail", this.fail);
        m.put("cpuRounds", this.cpuRounds);
        m.put("maxConcurrent", this.maxConcurrent);
        return m;
    }

    private static final Pattern WORD = Pattern.compile("\"(name|sku)\":\"([a-z]+)-(\\d+)\"");

    /** JIT 가 데워지기 전과 후의 차이가 드러나도록 여러 종류의 코드를 고루 돈다 */
    static String cpuWork(int rounds) throws Exception {
        ThreadLocalRandom r = ThreadLocalRandom.current();
        MessageDigest sha = MessageDigest.getInstance("SHA-256");
        byte[] last = new byte[0];
        for (int round = 0; round < rounds; round++) {
            List<Map<String, Object>> items = new ArrayList<>();
            for (int i = 0; i < 40; i++) {
                Map<String, Object> it = new LinkedHashMap<>();
                it.put("name", "item-" + r.nextInt(100000));
                it.put("sku", "sku-" + r.nextInt(1000));
                it.put("price", r.nextDouble(1, 1000));
                it.put("qty", r.nextInt(1, 10));
                items.add(it);
            }
            items.sort(Comparator.comparingDouble(m -> (Double) m.get("price")));
            StringBuilder sb = new StringBuilder("[");
            for (Map<String, Object> it : items) {
                sb.append(String.format("{\"name\":\"%s\",\"sku\":\"%s\",\"price\":%.2f,\"qty\":%d},",
                        it.get("name"), it.get("sku"), it.get("price"), it.get("qty")));
            }
            sb.append(']');
            Matcher m = WORD.matcher(sb);
            long sum = 0;
            while (m.find()) sum += Long.parseLong(m.group(3));
            sha.update(sb.toString().getBytes());
            sha.update(Long.toString(sum).getBytes());
            last = sha.digest();
        }
        return HexFormat.of().formatHex(last, 0, 8);
    }
}
